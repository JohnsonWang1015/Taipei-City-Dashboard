package controllers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"TaipeiCityDashboardBE/app/models"

	"github.com/gin-gonic/gin"
)

// GeoJSON feature types
type geoJSONFeature struct {
	Type       string                 `json:"type"`
	Geometry   json.RawMessage        `json:"geometry"`
	Properties map[string]interface{} `json:"properties"`
}

type geoJSONFeatureCollection struct {
	Type     string           `json:"type"`
	Features []geoJSONFeature `json:"features"`
}

/*
GetComponentGeoData serves GeoJSON FeatureCollection from PostGIS tables.
GET /api/v1/component/:id/geo?city=taipei

Looks up the component's map_config to find the table name (component_maps.index),
then queries DBDashboard for rows with wkb_geometry, returning GeoJSON.
*/
func GetComponentGeoData(c *gin.Context) {
	// 1. Get component ID
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "Invalid component ID"})
		return
	}

	// 2. Get city
	var query componentQuery
	c.ShouldBindQuery(&query)
	if query.City == "" {
		query.City = "taipei"
	}

	// 3. Get map config IDs from query_charts
	mapConfigIDs, err := models.GetComponentMapConfigIDs(id, query.City)
	if err != nil || len(mapConfigIDs) == 0 {
		c.JSON(http.StatusNotFound, gin.H{"status": "error", "message": "No map config found"})
		return
	}

	// 4. Get the first map config to find the table name
	var mapConfig models.ComponentMap
	result := models.DBManager.Where("id = ?", mapConfigIDs[0]).First(&mapConfig)
	if result.Error != nil {
		c.JSON(http.StatusNotFound, gin.H{"status": "error", "message": "Map config not found"})
		return
	}

	tableName := mapConfig.Index

	// 5. Query DBDashboard for GeoJSON data
	features, err := getGeoJSONFromTable(tableName)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}

	// 6. Return GeoJSON FeatureCollection
	fc := geoJSONFeatureCollection{
		Type:     "FeatureCollection",
		Features: features,
	}
	c.JSON(http.StatusOK, fc)
}

// getGeoJSONFromTable reads rows with wkb_geometry from a PostGIS table
// and converts them to GeoJSON features.
func getGeoJSONFromTable(tableName string) ([]geoJSONFeature, error) {
	// Use parameterized query for the column list, but table name must be sanitized
	// since GORM doesn't support parameterized table names
	if !isValidTableName(tableName) {
		return nil, fmt.Errorf("invalid table name: %s", tableName)
	}

	query := fmt.Sprintf(
		`SELECT *, ST_AsGeoJSON(wkb_geometry)::json as _geojson FROM "%s" LIMIT 10000`,
		tableName,
	)

	rows, err := models.DBDashboard.Raw(query).Rows()
	if err != nil {
		return nil, fmt.Errorf("query failed for table %s: %w", tableName, err)
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}

	var features []geoJSONFeature

	for rows.Next() {
		// Create a slice of interface{} to hold each column value
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range values {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			continue
		}

		properties := make(map[string]interface{})
		var geometry json.RawMessage

		for i, colName := range columns {
			val := values[i]
			if colName == "_geojson" {
				// This is the GeoJSON geometry
				if b, ok := val.([]byte); ok {
					geometry = json.RawMessage(b)
				}
			} else if colName == "wkb_geometry" || colName == "ogc_fid" {
				// Skip internal columns
				continue
			} else {
				// Convert byte arrays to strings for JSON
				if b, ok := val.([]byte); ok {
					properties[colName] = string(b)
				} else {
					properties[colName] = val
				}
			}
		}

		if geometry == nil {
			continue
		}

		features = append(features, geoJSONFeature{
			Type:       "Feature",
			Geometry:   geometry,
			Properties: properties,
		})
	}

	if features == nil {
		features = []geoJSONFeature{}
	}

	return features, nil
}

// isValidTableName prevents SQL injection by allowing only alphanumeric and underscore characters.
func isValidTableName(name string) bool {
	for _, c := range name {
		if !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_') {
			return false
		}
	}
	return len(name) > 0 && len(name) <= 128
}
