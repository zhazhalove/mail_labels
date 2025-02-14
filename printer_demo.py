from PIL import Image, ImageWin
import win32print, win32ui
import io, platform


class DymoPrinter:
    def __init__(self, printer_name="DYMO LabelWriter 4XL"):
        self.printer_name = printer_name
        self.os_type = platform.system()
        self.label_width = 1200   # 4 inches at 300 DPI
        self.label_height = 1800  # 6 inches at 300 DPI
 
    def print_label(self, image_bytes):
        """
        Prints a PNG label from bytes using the Dymo LabelWriter 4XL.
        Supports Windows only.
        """
        try:
            if self.os_type != "Windows":
                print(f"Unsupported OS: {self.os_type}. Printing is only supported on Windows.")
                return
 
            # Load and resize image while maintaining aspect ratio
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert("RGB")  # Ensure compatibility with Windows printing
            image = self._resize_image(image)
 

            # Rotate the image to **landscape mode**
            # image = image.rotate(-90, expand=True)

            image.save('output_png/test.png', 'PNG')

          
            self._print_windows(image)
 
        except Exception as e:
            print(f"Error loading image: {e}")
 
    def _resize_image(self, image):
        """
        Resizes the image to fit **inside** the 4" x 6" (1200x1800) label while maintaining aspect ratio.
        NO cropping or additional padding.
        """
        # Compute aspect ratios
        image_aspect = image.width / image.height
        label_aspect = self.label_width / self.label_height
 
        # Determine new size while maintaining aspect ratio
        if image_aspect > label_aspect:
            # Image is wider than the label: Scale based on width
            new_width = self.label_width
            new_height = int(new_width / image_aspect)
        else:
            # Image is taller than the label: Scale based on height
            new_height = self.label_height
            new_width = int(new_height * image_aspect)
 
        # Resize image while maintaining aspect ratio
        return image.resize((new_width, new_height), Image.LANCZOS)
 
    def _print_windows(self, image):
        """
        Sends the resized PNG image to the printer on Windows using win32print.
        """
        try:
            import win32print
            import win32ui
            from PIL import ImageWin
 
            hprinter = win32print.OpenPrinter(self.printer_name)
            printer_info = win32print.GetPrinter(hprinter, 2)
            printer_name = printer_info["pPrinterName"]
 
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
 
            hdc.StartDoc("Label Print")
            hdc.StartPage()
 
            # dib = ImageWin.Dib(image)
 
            # Draw the resized image at full label size
            # dib.draw(hdc.GetHandleOutput(), (0, 0, image.width, image.height))
 
            # Convert image to raw data for printing
            bmp = image.convert("RGB")  # Ensure it's in RGB mode
            raw_data = bmp.tobytes("raw", "BGRX")  # Convert to Windows-compatible BMP format

            # Send raw data to printer
            hdc.WritePrinter(raw_data)

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
 
            win32print.ClosePrinter(hprinter)
            
            print(f"Printed label on {self.printer_name}")
 
        except Exception as e:
            print(f"Error printing on Windows: {e}")


# Example Usage
if __name__ == "__main__":
    with open("output_png\document_20250214122454_b83f5167-411a-4360-a14a-59b9f84f58e9.png", "rb") as f:
        image_data = f.read()
        printer = DymoPrinter()
        printer.print_label(image_data)
