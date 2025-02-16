from PIL import Image, ImageOps
from io import BytesIO
import base64

if __name__ == "__main__":

    # Image and Label Specs
    IMAGE_PATH = 'output_png/document_20250213213449_5b0ca6f4-e21c-4033-80af-e816a2de3ef5.png'
    OUTPUT_DYMO_LABEL_PATH = 'output_png/label.dymo'

    # Target label dimensions in pixels (6" x 4" at 300 DPI)
    LABEL_WIDTH_PX = 1800  # 6 inches * 300 DPI
    LABEL_HEIGHT_PX = 1200  # 4 inches * 300 DPI
    TARGET_DPI = 300  # Desired DPI for printing

    # Convert to grayscale
    image = Image.open(IMAGE_PATH).convert("L")

    # Resize while maintaining aspect ratio (adds white space if necessary)
    image_scaled = ImageOps.contain(image, (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), Image.Resampling.LANCZOS)

    # Save resized image with explicit 300 DPI setting
    image_scaled.save('output_png/test.png', dpi=(TARGET_DPI, TARGET_DPI), format="PNG")

    # Encode the image in Base64
    buffer = BytesIO()
    image_scaled.save(buffer, format="PNG")
    encoded_bytes = base64.b64encode(buffer.getvalue())  # Encode as Base64
    encoded_string = encoded_bytes.decode("ascii")  # Decode bytes to ASCII string

    # Define the Dymo Label XML template with embedded Base64 image
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

    # Write the XML label to a .dymo file
    with open(OUTPUT_DYMO_LABEL_PATH, "w", encoding="utf-8") as file:
        file.write(dymo_label_xml)

    print(f"Dymo label file saved as {OUTPUT_DYMO_LABEL_PATH}")
