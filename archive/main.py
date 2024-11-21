from flask import Flask, jsonify
from flask_cors import CORS
from osgeo import ogr
import os

app = Flask(__name__)
CORS(app)

# Path to the output directory where line shapefiles are stored
output_dir = r'C:\Users\beqa4\OneDrive\Desktop\PNG_TO_LINES-main\Output_Shapefiles'

def shapefile_to_geojson(shapefile_path):
    """Convert shapefile to GeoJSON."""
    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.Open(shapefile_path, 0)  # Open shapefile in read-only mode
    if not data_source:
        return {"error": f"Unable to open {shapefile_path}"}

    layer = data_source.GetLayer()
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    for feature in layer:
        geom = feature.GetGeometryRef()
        geojson["features"].append({
            "type": "Feature",
            "geometry": eval(geom.ExportToJson()),  # Convert geometry to GeoJSON
            "properties": {key: feature.GetField(key) for key in feature.keys()}
        })

    data_source = None  # Close the shapefile
    return geojson

@app.route('/get-lines', methods=['GET'])
def get_lines():
    geojson_collections = []
    # Iterate over folders in the output directory
    for hash_folder in os.listdir(output_dir):
        line_folder = os.path.join(output_dir, hash_folder, "Line")
        if not os.path.isdir(line_folder):
            continue

        # Find the line shapefile
        for file in os.listdir(line_folder):
            if file.endswith(".shp"):
                shapefile_path = os.path.join(line_folder, file)
                geojson = shapefile_to_geojson(shapefile_path)
                geojson_collections.append(geojson)

    return jsonify(geojson_collections)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
