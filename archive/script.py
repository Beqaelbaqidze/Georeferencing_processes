import os
import subprocess

# Paths to the scripts
png_to_points_script = "PNG_To_Points.py"
points_to_lines_script = "Points_To_Lines.py"

# Ensure the paths to the scripts are valid
if not os.path.exists(png_to_points_script):
    print(f"Error: {png_to_points_script} not found.")
    exit(1)

if not os.path.exists(points_to_lines_script):
    print(f"Error: {points_to_lines_script} not found.")
    exit(1)

# Step 1: Run PNG_To_Points.py
print("Running PNG_To_Points.py...")
try:
    subprocess.run(["python", png_to_points_script], check=True)  # Waits for completion
    print("PNG_To_Points.py completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error running PNG_To_Points.py: {e}")
    exit(1)

# Step 2: Run points_to_lines.py
print("Running points_to_lines.py...")
try:
    subprocess.run(["python", points_to_lines_script], check=True)  # Waits for completion
    print("points_to_lines.py completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error running points_to_lines.py: {e}")
    exit(1)

print("All scripts executed successfully.")
