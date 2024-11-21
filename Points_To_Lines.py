import hashlib
import os
from osgeo import ogr
import numpy as np
from scipy.spatial import KDTree

# Load points from a shapefile and return their coordinates and geometries
def load_points(shapefile_path):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.Open(shapefile_path, 0)  # 0 means read-only
    layer = data_source.GetLayer()

    points = []
    coords = []
    for feature in layer:
        geom = feature.GetGeometryRef()
        if geom.GetGeometryType() == ogr.wkbPoint:
            points.append(geom.Clone())  # Store geometry
            coords.append((geom.GetX(), geom.GetY()))  # Store coordinates
    data_source = None  # Close the data source
    return points, coords

# Create lines based on the distance threshold rule
def create_lines(points, coords, max_distance):
    kdtree = KDTree(coords)
    visited = set()
    lines = []  # Store multiple lines

    for start_idx in range(len(coords)):
        if start_idx in visited:
            continue  # Skip if this point has already been visited

        # Start a new line
        line = ogr.Geometry(ogr.wkbLineString)
        current_idx = start_idx
        line.AddPoint(*coords[current_idx])
        visited.add(current_idx)

        while True:
            # Find the nearest unvisited neighbor within the distance threshold
            distances, nearest_idxs = kdtree.query(coords[current_idx], k=10)  # Find multiple neighbors
            
            found_nearby = False
            for dist, idx in zip(distances, nearest_idxs):
                if idx != current_idx and idx not in visited and dist <= max_distance:
                    # Add this point to the line if it's within the distance threshold
                    line.AddPoint(*coords[idx])
                    visited.add(idx)
                    current_idx = idx
                    found_nearby = True
                    break
            
            # If no nearby unvisited points within the threshold are found, end the current line
            if not found_nearby:
                break

        # Add the completed line to the list of lines
        if line.GetPointCount() > 1:  # Ensure the line has more than one point
            lines.append(line)

    return lines

# Save multiple lines to a new shapefile
def save_lines(output_shapefile, lines, spatial_ref):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    out_data_source = driver.CreateDataSource(output_shapefile)
    out_layer = out_data_source.CreateLayer("lines", spatial_ref, ogr.wkbLineString)

    # Create a field for storing line IDs
    field_defn = ogr.FieldDefn("LineID", ogr.OFTInteger)
    out_layer.CreateField(field_defn)

    # Add each line to the shapefile
    for i, line in enumerate(lines):
        feature_defn = out_layer.GetLayerDefn()
        feature = ogr.Feature(feature_defn)
        feature.SetGeometry(line)
        feature.SetField("LineID", i)
        out_layer.CreateFeature(feature)
        feature = None  # Free the feature to release resources

    out_data_source = None  # Close the output data source
    print(f"Shapefile with connected lines created successfully: {output_shapefile}")

# Compute MD5 hash from a filename
def md5_hash(filename):
    return hashlib.md5(filename.encode("utf-8")).hexdigest()

# Main function to orchestrate the process
def main(base_folder, max_distance_cm):
    for hash_folder in os.listdir(base_folder):
        hash_folder_path = os.path.join(base_folder, hash_folder)

        # Ensure this is a directory
        if not os.path.isdir(hash_folder_path):
            continue

        points_folder = os.path.join(hash_folder_path, "Points")
        line_folder = os.path.join(hash_folder_path, "Line")

        # Check if the Line folder already exists
        if os.path.exists(line_folder):
            print(f"Line folder already exists for {hash_folder}. Skipping...")
            continue

        # If Points folder doesn't exist, skip
        if not os.path.exists(points_folder):
            print(f"No Points folder in {hash_folder}. Skipping...")
            continue

        # Find points shapefile in Points folder
        points_shapefile = None
        for file in os.listdir(points_folder):
            if file.startswith("points_") and file.endswith(".shp"):
                points_shapefile = os.path.join(points_folder, file)
                break

        if not points_shapefile:
            print(f"No points shapefile found in {points_folder}. Skipping...")
            continue

        # Create the Line folder
        os.makedirs(line_folder, exist_ok=True)

        # Define output line shapefile path
        line_shapefile_path = os.path.join(line_folder, f"line_{hash_folder}.shp")

        # Load points from the points shapefile
        points, coords = load_points(points_shapefile)
        spatial_ref = points[0].GetSpatialReference()  # Use spatial reference from the first point

        # Convert max distance from cm to the coordinate system units (assuming meters)
        max_distance = max_distance_cm / 100.0  # Convert cm to meters

        # Create lines with the specified distance rule
        lines = create_lines(points, coords, max_distance)

        # Save the created lines to an output shapefile
        save_lines(line_shapefile_path, lines, spatial_ref)

# Run the main function

if __name__ == "__main__":
    base_folder = r"C:\Users\beqa4\OneDrive\Desktop\PNG_TO_LINES-main\Output_Shapefiles"
    max_distance_cm = 1.1  # Maximum distance in cm
    main(base_folder, max_distance_cm)
