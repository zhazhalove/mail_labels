"""
This script demonstrates asynchronous processing of PDF documents using asyncio,
zeromq for message passing, and a process pool to handle blocking PDF operations.
It implements a producer-consumer pattern with improved error handling and shutdown.
"""

import zmq, zmq.asyncio, asyncio, time, fitz, io, win32print, win32ui, structlog, logging.config, yaml, uuid, sys
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageChops
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor



PNG_OUTPUT_FOLDER = Path("output_png")
PNG_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_CONFIG = "logging_config.yaml"


# Load Logging Configuration
with open(LOG_CONFIG, "r") as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,  # Ensures log levels are structured
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True
)

logger = structlog.get_logger()
# logger = structlog.get_logger("PDFMailShipmentDebug")

# Type Variable for Generics
T = TypeVar('T')

# Abstract Printer Class
class AbstractPrinter(ABC, Generic[T]):
    @abstractmethod
    def print_document(self, document: T) -> None:
        """
        Print the given document.
        """
        pass

    @abstractmethod
    def configure_printer(self, settings: dict) -> None:
        """
        Configure the printer with the provided settings.
        """
        pass

    @abstractmethod
    def get_status(self) -> str:
        """
        Retrieve the current status of the printer.
        """
        pass

# Dymo Printer Implementation
class DymoPrinterWin(AbstractPrinter[bytes]):
    def __init__(self, printer_name: str):
        self.printer_name = printer_name
        self.settings = {}
    
    def print_document(self, document: bytes) -> None:
        """
        Send a document to the Dymo printer over a Windows network.
        """
        if not document:
            logger.error("No document content to print.", script=sys.argv[0])
            return
        
     

        try:
            # Open printer
            printer_handle = win32print.OpenPrinter(self.printer_name)
            printer_info = win32print.GetPrinter(printer_handle, 2)
            printer_device = win32ui.CreateDC()
            printer_device.CreatePrinterDC(self.printer_name)
            
            # Start document
            job_id = win32print.StartDocPrinter(printer_handle, 1, ("Print Job", None, "RAW"))
            win32print.StartPagePrinter(printer_handle)
            
            # Write data directly to the printer
            win32print.WritePrinter(printer_handle, document)
            
            win32print.EndPagePrinter(printer_handle)
            win32print.EndDocPrinter(printer_handle)
            logger.info("Document printed successfully", printer=self.printer_name, script=sys.argv[0])
        
        except Exception as e:
            logger.exception("Printing failed", error=str(e), script=sys.argv[0])
        
        finally:
            win32print.ClosePrinter(printer_handle)
    
    def configure_printer(self, settings: dict) -> None:
        """
        Apply configuration settings to the Dymo printer.
        """
        self.settings.update(settings)
        logger.info("Printer configured", printer=self.printer_name, settings=self.settings, script=sys.argv[0])
    
    def get_status(self) -> str:
        """
        Retrieve printer status.
        """
        pass

# Document Representation
class Document:
    def __init__(self, content: bytes, filename: str = None):
        self.content: bytes = content
        self.filename: str = filename or f"document_{time.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4()}"

# Document Processor Interface
class DocumentProcessor(ABC, Generic[T]):
    @abstractmethod
    async def process(self, document: Document) -> T:
        pass

# PDF Processor Implementation
class PdfProcessor(DocumentProcessor[bytes]):
    def __init__(self):
        self.executor = ThreadPoolExecutor()

    async def process(self, document: Document) -> bytes:
        try:
            pdf_data = document.content
            loop = asyncio.get_running_loop()
            img_bytes = await loop.run_in_executor(self.executor, PdfProcessor.Process_pdf_sync, pdf_data)
            return img_bytes
        except Exception as e:
            logger.error("Error processing PDF", error=str(e), script=sys.argv[0])
            return None  # Return None on error

    def shutdown(self):
        """Ensure process pool executor shuts down cleanly."""
        self.executor.shutdown(wait=True, cancel_futures=True)
    
    @staticmethod
    def Process_pdf_sync(pdf_data: bytes) -> bytes:
        try:
            with fitz.open(stream=pdf_data, filetype="pdf") as doc:
                if len(doc) > 0:  # Ensure the document has at least one page
                    pixmap = doc[0].get_pixmap()
                    
                    # Convert to PIL Image
                    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                    
                    # Step 1: Auto-crop whitespace
                    # Convert image to grayscale and get the bounding box of non-white pixels
                    bg = Image.new("RGB", image.size, "white")  # White background for comparison
                    diff = ImageChops.difference(image, bg)
                    bbox = diff.getbbox()  # Get bounding box of content
                    
                    if bbox:
                        image = image.crop(bbox)  # Crop to content

                    # Step 2: Resize while maintaining aspect ratio
                    #
                    # Target Dymo Label Size in Pixels (300 DPI)
                    # 
                    # DPI (Dots Per Inch) means how many pixels (dots) are in one inch. 
                    # The given label dimensions are:
                    #   - Width: 104 mm
                    #   - Height: 159 mm
                    # 
                    # To convert millimeters to inches, use:
                    #   1 inch = 25.4 mm
                    # 
                    # So, the width and height in inches are:
                    #   width_in_inches  = 104 mm  / 25.4 ≈ 4.094 inches
                    #   height_in_inches = 159 mm  / 25.4 ≈ 6.260 inches
                    #
                    # Since the label printer works at 300 DPI, multiply by 300:
                    #   target_width  = 4.094 inches  * 300 ≈ 1228 pixels
                    #   target_height = 6.260 inches  * 300 ≈ 1879 pixels
                    #
                    # These values define the expected image size in pixels when printing at 300 DPI
                    target_width = 1228
                    target_height = 1879
                    image.thumbnail((target_width, target_height), Image.LANCZOS)

                    # Convert back to bytes
                    with io.BytesIO() as output:
                        image.save(output, format="PNG")  # Save as PNG
                        return output.getvalue()
                else:
                    logger.error("Error: PDF document is empty.", script=sys.argv[0])
                    return None
        except Exception as e:
            logger.error("Error in Process_pdf_sync", error=str(e), script=sys.argv[0])
            return None


# Message Queue Abstraction
class MessageQueue(ABC, Generic[T]):
    @abstractmethod
    async def put(self, item: T) -> None:
        pass

    @abstractmethod
    async def get(self) -> T:
        pass

    @abstractmethod
    def empty(self) -> bool:
        pass

    @abstractmethod
    async def join(self) -> None:
        pass

    @abstractmethod
    def task_done(self) -> None:
        pass

# Async Queue Implementation
class AsyncQueue(MessageQueue[Document]):
    def __init__(self, maxsize: int = 0):
        self._queue: asyncio.Queue[Document] = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: Document) -> None:
        await self._queue.put(item)

    async def get(self) -> Document:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()

    def qsize(self):
        return self._queue.qsize()

    async def join(self) -> None:
        await self._queue.join()

    def task_done(self) -> None:
        self._queue.task_done()


# Producer
async def producer(queue: MessageQueue[Document], zmq_socket: zmq.asyncio.Socket, shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set():
        try:
            pdf_data: bytes = await zmq_socket.recv(flags=zmq.NOBLOCK)
            document = Document(pdf_data)  # , filename="received.pdf"  # You could add filename here if sender provides it
            await queue.put(document)
            logger.info("Producer received document", filename=document.filename, script=sys.argv[0])
        except zmq.Again:
            await asyncio.sleep(0.01) # Prevent high CPU usage
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Producer error", error=str(e), script=sys.argv[0])

    logger.info("Producer finished.", script=sys.argv[0])


# Consumer
async def consumer(queue: MessageQueue[Document], processor: DocumentProcessor[bytes], shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set() or not queue.empty():
        try:
            document: Document = await queue.get()
            
            logger.info("Consumer processing document", filename=document.filename, script=sys.argv[0])

            # Skip processing if shutdown was requested
            if shutdown_event.is_set():
                logger.info("Shutdown detected, skipping processing", filename=document.filename, script=sys.argv[0])
                break

            result: bytes = await processor.process(document)
            
      
            if result:
                output_filename = PNG_OUTPUT_FOLDER.joinpath(f"{document.filename}.png")
                with open(output_filename, "wb") as f:
                    f.write(result)
                logger.info("Consumer processed and saved image", output_filename=str(output_filename), script=sys.argv[0])
            else:
                logger.error("Processing failed for document", filename=document.filename, script=sys.argv[0])

            # if result:
            #     dymo_printer = DymoPrinterWin("\\\\network-printer-name")
            #     dymo_printer.configure_printer({"dpi": 300, "paper_size": "104mm x 159mm"})
            #     dymo_printer.print_document(result)
            # else:
            #     print(f"Printing failed for document: {document.filename}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Consumer error", error=str(e), script=sys.argv[0])
            queue.task_done()
        else:
            queue.task_done()

    logger.info("Consumer finished.", script=sys.argv[0])


# Main Function
async def main() -> None:
    queue: MessageQueue[Document] = AsyncQueue(maxsize=10)
    processor: DocumentProcessor[bytes] = PdfProcessor()
    shutdown_event = asyncio.Event()

    context: zmq.asyncio.Context = zmq.asyncio.Context()
    socket: zmq.asyncio.Socket = context.socket(zmq.PULL)
    socket.bind("tcp://*:5555")  # Bind to the ZeroMQ socket

    producer_task = asyncio.create_task(producer(queue, socket, shutdown_event))
    consumer_task = asyncio.create_task(consumer(queue, processor, shutdown_event))

    try:
        logger.info("Service started. Press Ctrl+C to stop.", script=sys.argv[0])
        
        while not shutdown_event.is_set():
            await asyncio.sleep(10)  # Simulate some work

    except KeyboardInterrupt:
        logger.warning("Service interrupted. Shutting down...", script=sys.argv[0])

        shutdown_event.set()  # Signal shutdown

        await queue.join()  # Wait for queue to be empty

        # Use gather instead of wait for better task handling
        results = await asyncio.gather(producer_task, consumer_task, return_exceptions=True)

        # Log any exceptions instead of letting them crash shutdown
        for result in results:
            if isinstance(result, Exception):
                logger.exception("Task error during shutdown", error=str(result), script=sys.argv[0])

    finally:
        logger.info("Shutting down PdfProcessor...", script=sys.argv[0])
        processor.shutdown()

        logger.info("Closing ZeroMQ sockets...", script=sys.argv[0])
        socket.close()
        context.term()
        
        logger.info("Shutdown complete.", script=sys.argv[0])


if __name__ == "__main__":
    try:
        asyncio.run(main())
        # asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        logger.warning("Service interrupted. Exiting gracefully...", script=sys.argv[0])
