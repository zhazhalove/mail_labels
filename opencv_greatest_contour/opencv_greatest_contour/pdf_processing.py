import os
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from .image_processing import find_largest_rectangle, highlight_rectangle, crop_rectangle


def pdf_to_image(pdf_path: str, page_num: int = 0) -> np.ndarray:
    """Convert a specified PDF page to an image format from a file path."""
    doc = fitz.open(pdf_path)  # Open the PDF file
    return _convert_pdf_page_to_image(doc, page_num)

def pdf_to_image_zoom(pdf_path: str, page_num: int = 0, zoom: float = 2.0) -> np.ndarray:
    """Convert a specified PDF page to an image format from a file path."""
    doc = fitz.open(pdf_path)  # Open the PDF file
    return _convert_pdf_page_to_image_zoom(doc, page_num, zoom=zoom)

def pdf_bytes_to_image(pdf_bytes: bytes, page_num: int = 0) -> np.ndarray:
    """Convert a specified PDF page to an image format from PDF bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # Open PDF from bytes
    return _convert_pdf_page_to_image(doc, page_num)

def pdf_bytes_to_image_zoom(pdf_bytes: bytes, page_num: int = 0, zoom: float = 2.0) -> np.ndarray:
    """Convert a specified PDF page to an image format from PDF bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # Open PDF from bytes
    return _convert_pdf_page_to_image_zoom(doc, page_num, zoom=zoom)

def _convert_pdf_page_to_image(doc: fitz.Document, page_num: int) -> np.ndarray:
    """Helper function to convert a PDF page to an image."""
    page = doc[page_num]  # Select the desired page
    pix = page.get_pixmap()  # Render the page as a pixel map
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # Convert to a PIL image
    return np.array(image)  # Convert the image to a NumPy array for OpenCV processing

def _convert_pdf_page_to_image_zoom(doc: fitz.Document, page_num: int, zoom: float = 2.0) -> np.ndarray:
    """Helper function to convert a PDF page to an image.
       Use default zoom scaling to imporve text quality
    """
    page = doc[page_num]  # Select the desired page
    matrix = fitz.Matrix(zoom, zoom) # Scale the image to incrase resolution
    pix = page.get_pixmap(matrix=matrix)  # Render the page as a pixel map
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # Convert to a PIL image
    return np.array(image)  # Convert the image to a NumPy array for OpenCV processing




def process_pdf_path_and_extract_label(pdf_path: str, output_path: str) -> None:
    """Extract the largest rectangular region from a PDF file path and save it as an image."""
    image = pdf_to_image(pdf_path)  # Convert PDF to image
    _process_image_and_save(image, output_path)


def process_pdf_bytes_and_extract_label(pdf_bytes: bytes, output_path: str) -> None:
    """Extract the largest rectangular region from a PDF bytes object and save it as an image."""
    image = pdf_bytes_to_image(pdf_bytes)  # Convert PDF bytes to image
    _process_image_and_save(image, output_path)


def _process_image_and_save(image: np.ndarray, output_path: str) -> None:
    """Helper function to process an image, detect contours, and save results."""
    largest_rect = find_largest_rectangle(image)  # Detect largest rectangle
    highlighted_image = highlight_rectangle(image, largest_rect)
    cropped_image = crop_rectangle(image, largest_rect)

    base, file = os.path.split(output_path)
    filename, ext = os.path.splitext(file)

    # Save the cropped image if detected
    if cropped_image is not None:
        cropped_pil = Image.fromarray(cropped_image)  # Convert cropped image to PIL format
        output_cropped_path = os.path.join(base, f"{filename}-cropped{ext}")
        cropped_pil.save(output_cropped_path)  # Save the image
        print(f"Cropped image saved to: {output_cropped_path}")
    else:
        print("No suitable contour found for cropping.")

    # Save the highlighted image if detected
    if highlighted_image is not None:
        highlighted_pil = Image.fromarray(highlighted_image)  # Convert highlighted image to PIL format
        output_highlighted_path = os.path.join(base, f"{filename}-highlighted{ext}")
        highlighted_pil.save(output_highlighted_path)  # Save the image
        print(f"Highlighted image saved to: {output_highlighted_path}")
    else:
        print("No suitable contour found to highlight.")
