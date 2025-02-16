import requests
import urllib3
import base64
from PIL import Image, ImageOps
from io import BytesIO

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API endpoints
STATUS_URL = "https://localhost:41951/DYMO/DLS/Printing/StatusConnected"
PRINT_URL = "https://localhost:41951/DYMO/DLS/Printing/PrintLabel"
DYMO_PRINTER_NAME = "DYMO LabelWriter 450"


# Image path (update with the actual image path)
IMAGE_PATH = "output_png/test.png"

def check_dymo_web_service():
    """Checks if the DYMO Web Service is running. If not, raises an exception."""
    try:
        response = requests.get(STATUS_URL, verify=False, timeout=5)
        if response.status_code == 200 and response.text.strip().lower() == "true":
            print("✅ DYMO Web Service is running.")
            return True
        else:
            raise Exception("❌ DYMO Web Service is not responding with 'true'.")
    except requests.RequestException as e:
        raise Exception(f"❌ Failed to connect to DYMO Web Service: {e}")


def encode_image_base64(image_path):
    """Loads an image, resizes it to fit DYMO label specs, and returns a Base64-encoded string."""
    try:
        with Image.open(image_path) as image:
            image = image.convert("L")  # Convert to grayscale

            # Use a memory buffer with a context manager for better cleanup
            with BytesIO() as buffer:
                image.save(buffer, format="PNG")
                encoded_bytes = base64.b64encode(buffer.getvalue())  # Encode as Base64
                return encoded_bytes.decode("ascii")  # Decode bytes to ASCII string

    except Exception as e:
        print(f"❌ Error encoding image: {e}")
        return None


# Check if the DYMO Web Service is running before proceeding
check_dymo_web_service()

# Encode image
encoded_string = encode_image_base64(IMAGE_PATH)

if not encoded_string:
    print("❌ Failed to encode image. Exiting.")
    exit(1)

# Define the DYMO Label XML with embedded Base64 image
dymo_label_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<DesktopLabel Version="1">
  <DYMOLabel Version="4">
    <Description>DYMO Label</Description>
    <Orientation>Landscape</Orientation>
    <LabelName>Shipping4x6 1744907</LabelName>
    <InitialLength>0</InitialLength>
    <BorderStyle>SolidLine</BorderStyle>
    <DYMORect>
      <DYMOPoint>
        <X>0.22</X>
        <Y>0.056666665</Y>
      </DYMOPoint>
      <Size>
        <Width>6.0000005</Width>
        <Height>4</Height>
      </Size>
    </DYMORect>
    <BorderColor>
      <SolidColorBrush>
        <Color A="1" R="0" G="0" B="0"></Color>
      </SolidColorBrush>
    </BorderColor>
    <BorderThickness>1</BorderThickness>
    <Show_Border>False</Show_Border>
    <HasFixedLength>False</HasFixedLength>
    <FixedLengthValue>0</FixedLengthValue>
    <DynamicLayoutManager>
      <RotationBehavior>ClearObjects</RotationBehavior>
      <LabelObjects>
        <ImageObject>
          <Name>ImageObject0</Name>
          <Brushes>
            <BackgroundBrush>
              <SolidColorBrush>
                <Color A="0" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </BackgroundBrush>
            <BorderBrush>
              <SolidColorBrush>
                <Color A="1" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </BorderBrush>
            <StrokeBrush>
              <SolidColorBrush>
                <Color A="1" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </StrokeBrush>
            <FillBrush>
              <SolidColorBrush>
                <Color A="0" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </FillBrush>
          </Brushes>
          <Rotation>Rotation0</Rotation>
          <OutlineThickness>1</OutlineThickness>
          <IsOutlined>False</IsOutlined>
          <BorderStyle>SolidLine</BorderStyle>
          <Margin>
            <DYMOThickness Left="0" Top="0" Right="0" Bottom="0" />
          </Margin>
          <Data>{encoded_string}</Data>
          <ScaleMode>Uniform</ScaleMode>
          <HorizontalAlignment>Center</HorizontalAlignment>
          <VerticalAlignment>Middle</VerticalAlignment>
          <ObjectLayout>
            <DYMOPoint>
              <X>0.22</X>
              <Y>0.06666666</Y>
            </DYMOPoint>
            <Size>
              <Width>5.980001</Width>
              <Height>3.9900005</Height>
            </Size>
          </ObjectLayout>
        </ImageObject>
      </LabelObjects>
    </DynamicLayoutManager>
  </DYMOLabel>
  <LabelApplication>Blank</LabelApplication>
  <DataTable>
    <Columns></Columns>
    <Rows></Rows>
  </DataTable>
</DesktopLabel>"""

# Define labelSetXml (for dynamic field replacement)
label_set_xml = """<LabelSet>
    <LabelRecord>
        <ObjectData Name="Text">Sample Label</ObjectData>
    </LabelRecord>
</LabelSet>"""

# Headers
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json"
}

# Form data
data = {
    "printerName": DYMO_PRINTER_NAME,
    "labelXml": dymo_label_xml,
    "labelSetXml": label_set_xml
}

try:
    # Send POST request
    response = requests.post(PRINT_URL, headers=headers, data=data, verify=False)

    # Print response
    print(f"🖨️ Status Code: {response.status_code}")
    print("🖨️ Response:", response.text)

except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")
