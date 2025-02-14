import requests
from PIL import Image, ImageOps

# DYMO Web Service URL (Ensure Dymo Connect is running)
DYMO_URL = "http://localhost:41951/DYMOPrintService/PrintLabel"

# Image and Label Specs
IMAGE_PATH = "your_image.png"
LABEL_WIDTH_MM = 101.6  # 4 inches in mm
LABEL_HEIGHT_MM = 152.4  # 6 inches in mm
DPI = 300

# Convert mm to pixels
LABEL_WIDTH_PX = int((LABEL_WIDTH_MM / 25.4) * DPI)
LABEL_HEIGHT_PX = int((LABEL_HEIGHT_MM / 25.4) * DPI)

# Load and resize image
image = Image.open(IMAGE_PATH)
image = ImageOps.contain(image, (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), Image.LANCZOS)

# Save resized image for debugging
image.save("resized_label.png")

# Convert image to base64 (DYMO API requires this format)
import base64
from io import BytesIO

buffer = BytesIO()
image.save(buffer, format="PNG")
img_base64 = base64.b64encode(buffer.getvalue()).decode()

# DYMO XML Label Template (Replace with actual label XML)
label_xml = f"""
<?xml version="1.0" encoding="utf-8"?>
<DieCutLabel Version="8.0" Units="twips">
    <PaperOrientation>Portrait</PaperOrientation>
    <Id>LargeShipping</Id>
    <PaperName>30256 Shipping</PaperName>
    <Objects>
        <ImageObject>
            <Name>Image</Name>
            <ForeColor Alpha="255" Red="0" Green="0" Blue="0"/>
            <BackColor Alpha="0" Red="255" Green="255" Blue="255"/>
            <ImageLocation>data:image/png;base64,{img_base64}</ImageLocation>
        </ImageObject>
    </Objects>
</DieCutLabel>
"""

# Print API Request
payload = {
    "printerName": "DYMO LabelWriter 4XL",
    "labelXml": label_xml,
    "printParamsXml": "",
    "labelSetXml": ""
}

headers = {"Content-Type": "application/json"}

response = requests.post(DYMO_URL, json=payload, headers=headers)

# Check response
if response.status_code == 200:
    print("Label printed successfully!")
else:
    print("Failed to print:", response.text)
