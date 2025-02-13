import cv2
import os
import uuid
import numpy as np
import fitz  # PyMuPDF - Library to work with PDFs
from PIL import Image  # Used for handling images
import matplotlib.pyplot as plt  # Used for displaying images

def pdf_to_image(pdf_path, page_num=0):
    """Convert a specified PDF page to an image format."""
    doc = fitz.open(pdf_path)  # Open the PDF file
    page = doc[page_num]  # Select the desired page
    pix = page.get_pixmap()  # Render the page as a pixel map
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # Convert to a PIL image
    return np.array(image)  # Convert the image to a NumPy array for OpenCV processing

def find_largest_rectangle(image):
    """Detect and return the largest rectangular contour in the given image."""
    image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)  # Convert image to grayscale
    edges = cv2.Canny(image_gray, 50, 150)  # Detect edges using Canny edge detection
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # Find external contours
    
    largest_rect = None  # Placeholder for the largest rectangle found
    largest_area = 0  # Track the largest area found
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)  # Get bounding rectangle
        area = w * h  # Calculate area
        if area > largest_area:  # Update if it's the largest so far
            largest_area = area
            largest_rect = (x, y, w, h)
    return largest_rect  # Return coordinates of the largest rectangle


# def highlight_and_crop(image, rect):
#     """Draw a rectangle around the largest detected contour and crop it."""
#     if rect:
#         x, y, w, h = rect
#         highlighted_image = image.copy()  # Create a copy to draw on
#         cv2.rectangle(highlighted_image, (x, y), (x + w, y + h), (0, 255, 0), 3)  # Draw a green rectangle
#         cropped_image = image[y:y + h, x:x + w]  # Crop the detected rectangle
#         return highlighted_image, cropped_image  # Return both highlighted and cropped images
#     return image, None  # Return original image if no rectangle is found

def highlight_rectangle(image, rect):
    """Draw a rectangle around the given contour."""
    if rect:
        x, y, w, h = rect
        highlighted_image = image.copy()  # Create a copy to draw on
        cv2.rectangle(highlighted_image, (x, y), (x + w, y + h), (0, 255, 0), 3)  # Draw a green rectangle
        return highlighted_image
    return image # Return the original image if no rectangle is found


def crop_rectangle(image, rect):
    """Crop the region defined by the given rectangle."""
    if rect:
        x, y, w, h = rect
        return image[y:y + h, x:x + w] # Crop the detected rectangle
    return None


def process_pdf_and_extract_label(pdf_path, output_path):
    """Extract the largest rectangular region (e.g., shipping label) from a PDF and save it as an image."""
    image = pdf_to_image(pdf_path)  # Convert PDF to image
    largest_rect = find_largest_rectangle(image)  # Detect largest rectangle
    highlighted_image = highlight_rectangle(image, largest_rect)
    cropped_image = crop_rectangle(image, largest_rect)
    # highlighted_image, cropped_image = highlight_and_crop(image, largest_rect)  # Highlight and crop
    
    # TEST CODE
    # # Display the image with the highlighted rectangle
    # plt.figure(figsize=(10, 10))
    # plt.imshow(cv2.cvtColor(highlighted_image, cv2.COLOR_BGR2RGB))
    # plt.axis("off")
    # plt.title("Highlighted Largest Contour")
    # plt.show()
    

    # Save the cropped image if detected
    if cropped_image is not None:
        cropped_pil = Image.fromarray(cropped_image)  # Convert cropped image to PIL format
        base, file = os.path.split(output_path)
        filename, ext = os.path.splitext(file)
        output_cropped_path = os.path.join(base, f"{filename}-cropped{ext}")
        cropped_pil.save(output_cropped_path)  # Save the image
        print(f"Cropped image saved to: {output_cropped_path}")
    else:
        print("No suitable contour found for cropping.")
    
    # Save the cropped image if detected
    if highlighted_image is not None:
        highlighted_pil = Image.fromarray(highlighted_image)  # Convert cropped image to PIL format
        base, file = os.path.split(output_path)
        filename, ext = os.path.splitext(file)
        output_highlighted_path = os.path.join(base, f"{filename}-highlighted{ext}")
        highlighted_pil.save(output_highlighted_path)  # Save the image
        print(f"hightlighted image saved to: {output_highlighted_path}")
    else:
        print("No suitable contour found to hightlight.")
    


if __name__ == "__main__":
    base_input_dir = "test_samples"
    base_output_dir = "output_png"

    # Ensure cross-platform compatibility
    pdf_path = os.path.join(base_input_dir, "Test_UPS_2025.pdf")
    output_path = os.path.join(base_output_dir, f"{uuid.uuid4().hex}.png")
    process_pdf_and_extract_label(pdf_path, output_path)  # Run the process


