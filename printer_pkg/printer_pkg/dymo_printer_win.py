from .abstract_printer import AbstractPrinter
import win32print, win32ui
import aiohttp
import asyncio
import urllib3
import base64
from PIL import Image
from io import BytesIO
from typing import Optional
import urllib.parse

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DymoPrinterError(Exception):
    """Custom exception for DymoPrinter errors."""
    pass

class DymoWebServiceError(Exception):
    """Custom exception for DymoWebService errors."""
    pass

class DymoLabel:
    """Represents a DYMO label with embedded image data."""
    def __init__(self, encoded_image: str):
        self.encoded_image = encoded_image
    
    def generate_label_xml(self) -> str:
        """Generates the full XML string for a DYMO label with the encoded image."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
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
          <Data>{self.encoded_image}</Data>
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
    
class DymoWebService:
    """Handles interactions with the DYMO Web Service for printing labels."""
    STATUS_URL = "https://localhost:41951/DYMO/DLS/Printing/StatusConnected"
    PRINT_URL = "https://localhost:41951/DYMO/DLS/Printing/PrintLabel"

    def __init__(self, printer_name: str = "DYMO LabelWriter 450"):
        self.printer_name = printer_name
        
    async def check_service_status(self) -> bool:
        """Checks if the DYMO Web Service is running asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:  # Async session management
                async with session.get(self.STATUS_URL, ssl=False, timeout=5) as response:  # Async HTTP GET request
                    response_text = await response.text()  # Await the response body
                    match response.status:
                        case 200 if response_text.strip().lower() == "true":
                            return True
                        case 200:
                            raise DymoWebServiceError("DYMO Web Service is running but not responding correctly.")
                        case _:
                            raise DymoWebServiceError(f"Unexpected response: {response.status}")
        except aiohttp.ClientError as e:
            raise DymoWebServiceError(f"Failed to connect to DYMO Web Service: {e}")
        except Exception as e:
            raise DymoWebServiceError(f"check_service_status exception: {e}")


    async def print_label(self, label: DymoLabel) -> bool:
        """Sends a print request to the DYMO Web Service."""
        
        label_xml = label.generate_label_xml()
        label_set_xml = """<LabelSet>
    <LabelRecord>
        <ObjectData Name="Text">Sample Label</ObjectData>
    </LabelRecord>
</LabelSet>"""
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        # Manually encode data just like requests does
        encoded_data = urllib.parse.urlencode({
            "printerName": self.printer_name,
            "labelXml": label_xml,
            "labelSetXml": label_set_xml
        })
   
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.PRINT_URL, headers=headers, data=encoded_data, ssl=False) as response:
                    response_text = await response.text()  # Await response text
                    match response.status:
                        case 200:
                          return True
                        case _:
                          raise DymoWebServiceError(f"Print request failed: {response.status} - {response_text}")
        except aiohttp.ClientError as e:
            raise DymoWebServiceError(f"Request to print label failed: {e}")
        except Exception as e:
            raise DymoWebServiceError(f"print_label exception: {e}")


# Dymo Printer Implementation
class DymoPrinter(AbstractPrinter[bytes], DymoWebService):

    def __init__(self, printer_name: str = "DYMO LabelWriter 450"):
        DymoWebService.__init__(self, printer_name)  # Call DymoWebService constructor
        self.settings = {}

    async def print_document(self, document: bytes) -> bool:
        """
        Converts the PNG image (in bytes) to grayscale, encodes it as Base64, 
        and sends it to the Dymo printer using the Dymo Web Service.
        """
        if not document:
            return False

        try:
            # Open image from bytes and process it
            with BytesIO(document) as image_stream:

                # convert to PIL
                with Image.open(image_stream) as image:

                    # Convert to grayscale
                    image = image.convert("L")

                    # Save the modified image to a buffer in PNG format
                    with BytesIO() as buffer:
                        image.save(buffer, format="PNG")

                        # Encode the processed grayscale image to Base64
                        encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")

            # Create label and print
            label = DymoLabel(encoded_image)

            await self.print_label(label)

            return True
        
        except DymoPrinterError as e:
            raise DymoPrinterError(f"print_document ERROR: {e}")
        except DymoWebServiceError as e:
            raise DymoPrinterError(f"DymoWebService ERROR: {e}")
        except Exception as e:
             raise DymoPrinterError(f"print_document exception: {e}")

    async def configure_printer(self, settings: dict) -> None:  # Made async
        """
        Apply configuration settings to the Dymo printer.
        """
        self.settings.update(settings)
        await asyncio.sleep(0)  # Ensures async compatibility (can be removed if not needed)

    async def get_status(self) -> str:
        """
        Retrieve printer status using the Dymo Web Service.
        """
        try:
            status = await self.check_service_status()  # Proper async call
            return "Online" if status else "Offline"
        except DymoPrinterError as e:
            raise DymoPrinterError(f"get_status ERROR: {e}")
        except DymoWebServiceError as e:
            raise DymoPrinterError(f"DymoWebService ERROR: {e}")
        except Exception as e:
          raise DymoPrinterError(f"DymoPrinter get_status exception: {e}")
