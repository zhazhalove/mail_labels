import asyncio
from printer_pkg import DymoPrinter, DymoPrinterError

async def main():
    # Initialize the printer
    printer = DymoPrinter(printer_name="DYMO LabelWriter 4XL")

    # Check if the printer is online
    status = await printer.get_status()
    print(f"Printer status: {status}")

    # Load an image file and send it for printing
    image_path = "output_png/test_UPS_Label.png"  # Provide the path to a PNG image

    try:
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()

        success = await printer.print_document(image_bytes)
        print("Print successful!" if success else "Print failed.")

    except DymoPrinterError as e:
        print(f"Dymo Printer Error: {e}")
    except FileNotFoundError as e:
        print(f"File Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
