import asyncio
from printer_pkg import DymoPrinter

async def main():
    # Initialize the printer
    printer = DymoPrinter(printer_name="DYMO LabelWriter 450")

    # Check if the printer is online
    status = await printer.get_status()
    print(f"Printer status: {status}")

    # Load an image file and send it for printing
    image_path = "output_png/test.png"  # Provide the path to a PNG image

    try:
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()

        success = await printer.print_document(image_bytes)
        print("Print successful!" if success else "Print failed.")
    except FileNotFoundError:
        print("Image file not found!")

if __name__ == "__main__":
    asyncio.run(main())
