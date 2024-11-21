from flask import Flask, request, jsonify, send_file
import fitz  # PyMuPDF
import cv2
import numpy as np
import os
from osgeo import gdal, ogr, osr
from scipy.spatial import KDTree
import geojson
import hashlib

app = Flask(__name__)

# Temporary directories for processing
TEMP_DIR = r"C:\Users\user\Desktop\PPRRJJ\PNG_TO_LINES-main\temp"
INPUT_DIR = os.path.join(TEMP_DIR, "input_pdf")
IMAGES_DIR = os.path.join(TEMP_DIR, "images")
OUTPUT_DIR = os.path.join(TEMP_DIR, "output_shapefiles")

# Create directories if they don't exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Helper functions
def md5_hash(filename):
    return hashlib.md5(filename.encode("utf-8")).hexdigest()


def convert_page_to_png(doc, page_num, output_file):
    page = doc[page_num]
    pix = page.get_pixmap(dpi=400, colorspace="gray")
    np_image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    bw_image = cv2.adaptiveThreshold(np_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    cv2.imwrite(output_file, bw_image)


def png_to_points(input_png, output_points_shp, scaling_factor=0.01):
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(32638)

    dataset = gdal.Open(input_png)
    geotransform = dataset.GetGeoTransform()
    origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform
    scaled_pixel_width = pixel_width * scaling_factor
    scaled_pixel_height = pixel_height * scaling_factor

    image = cv2.imread(input_png, cv2.IMREAD_GRAYSCALE)
    rows, cols = image.shape

    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(output_points_shp)
    layer = data_source.CreateLayer("points", source_srs, ogr.wkbPoint)
    points = []

    for row in range(rows):
        for col in range(cols):
            if image[row, col] == 0:
                x = origin_x + col * scaled_pixel_width
                y = origin_y + row * scaled_pixel_height
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint(x, y)
                feature = ogr.Feature(layer.GetLayerDefn())
                feature.SetGeometry(point)
                layer.CreateFeature(feature)
                points.append((x, y))
                feature.Destroy()

    data_source.Destroy()
    return points, source_srs


def points_to_lines(points, output_lines_shp, max_distance, scaling_factor=0.01):
    kdtree = KDTree(points)
    visited = set()
    lines = []

    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(output_lines_shp)
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(32638)
    layer = data_source.CreateLayer("lines", source_srs, ogr.wkbLineString)

    # Scale max distance using the scaling factor
    scaled_max_distance = max_distance * scaling_factor

    for start_idx in range(len(points)):
        if start_idx in visited:
            continue
        line = ogr.Geometry(ogr.wkbLineString)
        current_idx = start_idx
        line.AddPoint(*points[current_idx])
        visited.add(current_idx)

        while True:
            # Use the scaled maximum distance for nearest neighbor query
            distances, nearest_idxs = kdtree.query(points[current_idx], k=10)
            found_nearby = False
            for dist, idx in zip(distances, nearest_idxs):
                # Only connect points within the scaled distance
                if idx != current_idx and idx not in visited and dist <= scaled_max_distance:
                    line.AddPoint(*points[idx])
                    visited.add(idx)
                    current_idx = idx
                    found_nearby = True
                    break
            if not found_nearby:
                break

        if line.GetPointCount() > 1:
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetGeometry(line)
            layer.CreateFeature(feature)
            lines.append(line)
            feature.Destroy()

    data_source.Destroy()
    return lines



@app.route('/upload', methods=['POST'])
def upload_and_process():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    pdf_path = os.path.join(INPUT_DIR, file.filename)
    file.save(pdf_path)

    # Convert PDF to PNG
    doc = fitz.open(pdf_path)
    png_files = []
    for page_num in range(len(doc)):
        png_file = os.path.join(IMAGES_DIR, f"{os.path.splitext(file.filename)[0]}_page_{page_num + 1}.png")
        convert_page_to_png(doc, page_num, png_file)
        png_files.append(png_file)
    doc.close()

    # Process PNGs to Points and then Lines
    all_features = []
    scaling_factor = 0.0001  # Set the scaling factor for both points and lines
    for png_file in png_files:
        base_name = md5_hash(os.path.basename(png_file))
        points_shp = os.path.join(OUTPUT_DIR, f"{base_name}_points.shp")
        lines_shp = os.path.join(OUTPUT_DIR, f"{base_name}_lines.shp")

        points, spatial_ref = png_to_points(png_file, points_shp, scaling_factor=scaling_factor)
        lines = points_to_lines(points, lines_shp, max_distance=1.1, scaling_factor=scaling_factor)

        # Add lines to GeoJSON Feature Collection
        for line in lines:
            coords = []
            for i in range(line.GetPointCount()):
                coords.append((line.GetX(i), line.GetY(i)))
            feature = geojson.Feature(geometry=geojson.LineString(coords))
            all_features.append(feature)

    geojson_data = geojson.FeatureCollection(all_features)
    print(geojson_data)
    return jsonify(geojson_data), 200

if __name__ == '__main__':
    app.run(debug=True)