import hashlib
import os
from osgeo import gdal, ogr, osr
import cv2

# Input directory containing PNGs
input_dir = r'C:\Users\beqa4\OneDrive\Desktop\PNG_TO_LINES-main\Images'
output_dir = r'C:\Users\beqa4\OneDrive\Desktop\PNG_TO_LINES-main\Output_Shapefiles'

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Define a scaling factor
scaling_factor = 0.00001  # Change this value to scale up or down

# Define the source spatial reference system as EPSG:32638
source_srs = osr.SpatialReference()
source_srs.ImportFromEPSG(32638)

# Define the target spatial reference system as EPSG:4326
target_srs = osr.SpatialReference()
target_srs.ImportFromEPSG(32638)

# Set up transformation from source projection (EPSG:32638) to EPSG:4326
transform = osr.CoordinateTransformation(source_srs, target_srs)

# Define directions for neighbors (row_offset, col_offset)
directions = {
    0: (0, 1),    # 0 degrees
    45: (-1, 1),  # 45 degrees
    90: (-1, 0),  # 90 degrees
    135: (-1, -1),# 135 degrees
    180: (0, -1), # 180 degrees
    225: (1, -1), # 225 degrees
    270: (1, 0),  # 270 degrees
    315: (1, 1)   # 315 degrees
}

# Function to compute MD5 hash of a filename
def md5_hash(filename):
    return hashlib.md5(filename.encode('utf-8')).hexdigest()

# Process each PNG file in the input directory
for file_name in os.listdir(input_dir):
    if file_name.lower().endswith('.png'):
        input_png = os.path.join(input_dir, file_name)
        print(f"Processing {file_name}")

        # Generate MD5 hash for the output folder name
        base_name = os.path.splitext(file_name)[0]
        md5_name = md5_hash(base_name)

        # Create a folder with the MD5 name
        md5_folder = os.path.join(output_dir, md5_name)
        if not os.path.exists(md5_folder):
            os.makedirs(md5_folder)

        # Create the Points subfolder inside the MD5 folder
        points_folder = os.path.join(md5_folder, "Points")
        if not os.path.exists(points_folder):
            os.makedirs(points_folder)

        # Define the output shapefile path with the prefix `points_`
        output_shp = os.path.join(points_folder, f"points_{md5_name}.shp")

        # Skip processing if the shapefile already exists
        if os.path.exists(output_shp):
            print(f"Shapefile already exists: {output_shp}. Skipping...")
            continue

        # Open PNG with GDAL to get georeference
        dataset = gdal.Open(input_png)
        if not dataset:
            print(f"Cannot open {input_png}")
            continue

        # Get geotransform and projection
        geotransform = dataset.GetGeoTransform()
        origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform
        scaled_pixel_width = pixel_width * scaling_factor
        scaled_pixel_height = pixel_height * scaling_factor

        # Read PNG as a NumPy array with OpenCV
        image = cv2.imread(input_png, cv2.IMREAD_GRAYSCALE)
        if image is None:
            print(f"Cannot read image {input_png}")
            continue

        # Prepare output shapefile
        driver = ogr.GetDriverByName("ESRI Shapefile")
        if driver is None:
            raise RuntimeError("Shapefile driver is not available.")
        data_source = driver.CreateDataSource(output_shp)

        # Create layer with point geometry
        layer = data_source.CreateLayer("isolated_points", target_srs, ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("Direction", ogr.OFTInteger))

        # Iterate over each pixel and check for isolated neighbors
        rows, cols = image.shape
        for row in range(rows):
            for col in range(cols):
                pixel_value = int(image[row, col])

                # Only process black pixels (value 0)
                if pixel_value == 0:
                    for degree, (d_row, d_col) in directions.items():
                        neighbor_row = row + d_row
                        neighbor_col = col + d_col

                        # Check if neighbor is within bounds and has a black pixel
                        if (0 <= neighbor_row < rows) and (0 <= neighbor_col < cols):
                            if image[neighbor_row, neighbor_col] != 0:
                                # No black neighbor in this direction, export this point
                                x = origin_x + col * scaled_pixel_width
                                y = origin_y + row * scaled_pixel_height

                                # Transform coordinates to EPSG:4326
                                point = ogr.Geometry(ogr.wkbPoint)
                                point.AddPoint(x, y)
                                point.Transform(transform)

                                # Create feature and set attributes
                                feature = ogr.Feature(layer.GetLayerDefn())
                                feature.SetGeometry(point)
                                feature.SetField("Direction", degree)
                                layer.CreateFeature(feature)

                                # Destroy the feature to free resources
                                feature.Destroy()

        # Clean up and close the shapefile
        data_source.Destroy()
        dataset = None
        print(f"Shapefile created: {output_shp}")

print("Processing complete for all PNGs.")
