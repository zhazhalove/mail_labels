from PIL import Image, ImageOps

if __name__ == "__main__":

    # Image and Label Specs
    IMAGE_PATH = 'output_png/document_20250213213449_5b0ca6f4-e21c-4033-80af-e816a2de3ef5.png'
    LABEL_WIDTH_MM = 101.6  # 4 inches in mm
    LABEL_HEIGHT_MM = 152.4  # 6 inches in mm
    DPI = 300

    # Convert mm to pixels
    # 1 in = 25.4 mm
    LABEL_WIDTH_PX = int((LABEL_WIDTH_MM / 25.4) * DPI)
    LABEL_HEIGHT_PX = int((LABEL_HEIGHT_MM / 25.4) * DPI)

    # Load and resize image
    image = Image.open(IMAGE_PATH).convert("L")  # Convert to grayscal
    image_resize = ImageOps.contain(image, (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), Image.LANCZOS)
    
    # Save resized image for debugging
    image_resize.save('output_png/test.png')
