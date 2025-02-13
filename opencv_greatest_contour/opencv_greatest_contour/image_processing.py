import cv2
import numpy as np
from typing import Optional, Tuple

def find_largest_rectangle(image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """Detect and return the largest rectangular contour in the given image."""
    image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)  # Convert image to grayscale
    edges = cv2.Canny(image_gray, 50, 150)  # Detect edges using Canny edge detection
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # Find external contours
    
    largest_rect: Optional[Tuple[int, int, int, int]] = None  # Placeholder for the largest rectangle found
    largest_area: int = 0  # Track the largest area found
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)  # Get bounding rectangle
        area = w * h  # Calculate area
        if area > largest_area:  # Update if it's the largest so far
            largest_area = area
            largest_rect = (x, y, w, h)
    return largest_rect  # Return coordinates of the largest rectangle

def highlight_rectangle(image: np.ndarray, rect: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
    """Draw a rectangle around the given contour."""
    if rect:
        x, y, w, h = rect
        highlighted_image = image.copy()  # Create a copy to draw on
        cv2.rectangle(highlighted_image, (x, y), (x + w, y + h), (0, 255, 0), 3)  # Draw a green rectangle
        return highlighted_image
    return image  # Return the original image if no rectangle is found

def crop_rectangle(image: np.ndarray, rect: Optional[Tuple[int, int, int, int]]) -> Optional[np.ndarray]:
    """Crop the region defined by the given rectangle."""
    if rect:
        x, y, w, h = rect
        return image[y:y + h, x:x + w]  # Crop the detected rectangle
    return None
