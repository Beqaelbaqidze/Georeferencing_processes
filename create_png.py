import fitz  # PyMuPDF
import cv2
import numpy as np
import os
# Define input and output directories
input_dir = r'C:\Users\beqa4\OneDrive\Desktop\PNG_TO_LINES-main\Input_PDF'
output_dir = r'C:\Users\beqa4\OneDrive\Desktop\PNG_TO_LINES-main\Images'

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Function to convert a document page to a PNG image
def convert_page_to_png(doc, page_num, output_file):
    # Get the page
    page = doc[page_num]

    # Render the page to a pixmap
    pix = page.get_pixmap(dpi=400, colorspace="gray")

    # Convert pixmap to numpy array for OpenCV processing
    np_image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)

    # Apply adaptive thresholding to enhance black-and-white regions
    bw_image = cv2.adaptiveThreshold(np_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Save the image as PNG
    cv2.imwrite(output_file, bw_image)
    print(f"Saved PNG: {output_file}")

# Loop through all files in the input directory
for file_name in os.listdir(input_dir):
    if file_name.lower().endswith(('.pdf', '.djvu')):
        file_path = os.path.join(input_dir, file_name)
        print(f"Processing file: {file_name}")

        # Open the document
        doc = fitz.open(file_path)

        # Loop through all pages in the document
        for page_num in range(len(doc)):
            # Construct the output file name
            base_name = os.path.splitext(file_name)[0]
            output_file = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.png")
            convert_page_to_png(doc, page_num, output_file)

        # Close the document
        doc.close()

print("All files have been processed.")
