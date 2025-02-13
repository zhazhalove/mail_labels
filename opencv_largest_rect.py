import cv2
import os
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

def highlight_and_crop(image, rect):
    """Draw a rectangle around the largest detected contour and crop it."""
    if rect:
        x, y, w, h = rect
        highlighted_image = image.copy()  # Create a copy to draw on
        cv2.rectangle(highlighted_image, (x, y), (x + w, y + h), (0, 255, 0), 3)  # Draw a green rectangle
        cropped_image = image[y:y + h, x:x + w]  # Crop the detected rectangle
        return highlighted_image, cropped_image  # Return both highlighted and cropped images
    return image, None  # Return original image if no rectangle is found

def process_pdf_and_extract_label(pdf_path, output_cropped_path):
    """Extract the largest rectangular region (e.g., shipping label) from a PDF and save it as an image."""
    image = pdf_to_image(pdf_path)  # Convert PDF to image
    largest_rect = find_largest_rectangle(image)  # Detect largest rectangle
    highlighted_image, cropped_image = highlight_and_crop(image, largest_rect)  # Highlight and crop
    
    # Display the image with the highlighted rectangle
    plt.figure(figsize=(10, 10))
    plt.imshow(cv2.cvtColor(highlighted_image, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.title("Highlighted Largest Contour")
    plt.show()
    
    # Save the cropped image if detected
    if cropped_image is not None:
        cropped_pil = Image.fromarray(cropped_image)  # Convert cropped image to PIL format
        cropped_pil.save(output_cropped_path)  # Save the image
        print(f"Cropped image saved to: {output_cropped_path}")
        return output_cropped_path
    else:
        print("No suitable contour found for cropping.")
        return None

if __name__ == "__main__":
    base_input_dir = "test_samples"
    base_output_dir = "output_png"

    # Ensure cross-platform compatibility
    pdf_path = os.path.join(base_input_dir, "Test_UPS_2025.pdf")
    output_cropped_path = os.path.join(base_output_dir, "cropped_label.png")
    process_pdf_and_extract_label(pdf_path, output_cropped_path)  # Run the process




# import cv2
# import numpy as np
# import fitz  # PyMuPDF
# from PIL import Image
# import matplotlib.pyplot as plt

# def pdf_to_image(pdf_path, page_num=0):
#     """Convert a PDF page to an image."""
#     doc = fitz.open(pdf_path)
#     page = doc[page_num]
#     pix = page.get_pixmap()
#     image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#     return np.array(image)

# def find_largest_rectangle(image):
#     """Find and return the largest rectangular contour in the image."""
#     image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
#     edges = cv2.Canny(image_gray, 50, 150)
#     contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
#     largest_rect = None
#     largest_area = 0
#     for contour in contours:
#         x, y, w, h = cv2.boundingRect(contour)
#         area = w * h
#         if area > largest_area:
#             largest_area = area
#             largest_rect = (x, y, w, h)
#     return largest_rect

# def highlight_and_crop(image, rect):
#     """Highlight the largest contour and crop the image to that region."""
#     if rect:
#         x, y, w, h = rect
#         highlighted_image = image.copy()
#         cv2.rectangle(highlighted_image, (x, y), (x + w, y + h), (0, 255, 0), 3)
#         cropped_image = image[y:y + h, x:x + w]
#         return highlighted_image, cropped_image
#     return image, None

# def process_pdf_and_extract_label(pdf_path, output_cropped_path):
#     """Process the PDF and extract the largest rectangular label."""
#     image = pdf_to_image(pdf_path)
#     largest_rect = find_largest_rectangle(image)
#     highlighted_image, cropped_image = highlight_and_crop(image, largest_rect)
    
#     # Display highlighted image
#     plt.figure(figsize=(10, 10))
#     plt.imshow(cv2.cvtColor(highlighted_image, cv2.COLOR_BGR2RGB))
#     plt.axis("off")
#     plt.title("Highlighted Largest Contour")
#     plt.show()
    
#     # Save cropped image if found
#     if cropped_image is not None:
#         cropped_pil = Image.fromarray(cropped_image)
#         cropped_pil.save(output_cropped_path)
#         print(f"Cropped image saved to: {output_cropped_path}")
#         return output_cropped_path
#     else:
#         print("No suitable contour found for cropping.")
#         return None

# if __name__ == "__main__":
#     pdf_path = "test_sampels\Test_UPS_2025.pdf"  # Update this to your actual file path
#     output_cropped_path = "output_png\cropped_label.png"
#     process_pdf_and_extract_label(pdf_path, output_cropped_path)


