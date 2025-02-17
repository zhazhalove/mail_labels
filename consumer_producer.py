"""
This script demonstrates asynchronous processing of PDF documents using asyncio,
zeromq for message passing, and a process pool to handle blocking PDF operations.
It implements a producer-consumer pattern with improved error handling and shutdown.
"""

import zmq, zmq.asyncio, asyncio, io, structlog, logging.config, yaml, sys
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from PIL import Image, ImageOps
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from opencv_greatest_contour import pdf_bytes_to_image, find_largest_rectangle, crop_rectangle, pdf_bytes_to_image_zoom
from document_pkg import Document, DocumentProcessor
from io import BytesIO
from printer_pkg import DymoPrinter, DymoPrinterError


PNG_OUTPUT_FOLDER = Path("output_png")
PNG_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_CONFIG = "logging_config.yaml"


# Load Logging Configuration
with open(LOG_CONFIG, "r") as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),  # Adds a timestamp to log entries in ISO format.
        structlog.stdlib.add_log_level,  # Ensures log levels are included in the structured output.
        structlog.stdlib.PositionalArgumentsFormatter(),  # Formats positional arguments passed to log methods.
        structlog.processors.StackInfoRenderer(),  # Adds stack information to log entries when exceptions occur.
        structlog.processors.format_exc_info,  # Formats exception information for logging.
        structlog.processors.JSONRenderer()  # Renders the log entries as JSON.
    ],
    context_class=dict,  # Specifies that the context should be a standard Python dictionary.
    logger_factory=structlog.stdlib.LoggerFactory(),  # Uses the standard library's logging factory.
    wrapper_class=structlog.stdlib.BoundLogger,  # Uses the standard library's bound logger wrapper.
    cache_logger_on_first_use=True  # Caches the logger instance on first use for performance.
)

logger = structlog.get_logger()
# logger = structlog.get_logger("PDFMailShipmentDebug")

# Type Variable for Generics
T = TypeVar('T')


# PDF Processor Implementation
class PdfProcessorUPSCrop(DocumentProcessor[bytes]):

    def __init__(self):
        self.executor = ThreadPoolExecutor()

    async def process(self, document: Document) -> bytes:
        try:
            pdf_data = document.content
            loop = asyncio.get_running_loop()
            img_bytes = await loop.run_in_executor(self.executor, PdfProcessorUPSCrop.Process_pdf_sync, pdf_data)
            return img_bytes
        except Exception as e:
            pass

    @staticmethod
    def Process_pdf_sync(pdf_data: bytes) -> bytes:
        try:
            image_bytes = pdf_bytes_to_image_zoom(pdf_data) # Convert PDF bytes to image
            largest_rect = find_largest_rectangle(image_bytes)  # Detect largest rectangle
            cropped_image = crop_rectangle(image_bytes, largest_rect)

            if cropped_image is not None:
                # Convert the cropped NumPy array to a PIL image
                cropped_pil = Image.fromarray(cropped_image)

                with io.BytesIO() as output:
                    cropped_pil.save(output, format="PNG")  # Save as PNG
                    return output.getvalue()
            else:
                return None
        except Exception as e:
            logger.error("Error in Process_pdf_sync", error=str(e), script=sys.argv[0])
            return None


    def shutdown(self):
        """Ensure process pool executor shuts down cleanly."""
        self.executor.shutdown(wait=True, cancel_futures=True)


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
            
      
            # save original shipment label
            if result:
                output_filename = PNG_OUTPUT_FOLDER.joinpath(f"{document.filename}.png")
                with open(output_filename, "wb") as f:
                    f.write(result)
                logger.info("Consumer processed and saved image", output_filename=str(output_filename), script=sys.argv[0])
            else:
                logger.error("Processing failed for document", filename=document.filename, script=sys.argv[0])


            # print shipment label
            if result:

                printer = DymoPrinter(printer_name="DYMO LabelWriter 4XL")

                printer_status = await printer.get_status()

                if printer_status.strip().lower() != "online":
                     raise Exception(f"Printer is offline - {printer.printer_name}")
                
                
                # Target label dimensions in pixels (6" x 4" at 300 DPI)
                LABEL_WIDTH_PX = 1800  # 6 inches * 300 DPI
                LABEL_HEIGHT_PX = 1200  # 4 inches * 300 DPI
                TARGET_DPI = 300  # Desired DPI for printing

                # Open image from bytes and process it
                with BytesIO(result) as image_stream:

                    # convert to PIL
                    with Image.open(image_stream) as image:

                        # Convert to grayscale
                        image = image.convert("L")

                        # Resize while maintaining aspect ratio (adds white space if necessary)
                        image_scaled = ImageOps.contain(image, (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), Image.Resampling.LANCZOS)

                        # Save the modified image to a buffer in PNG format
                        with BytesIO() as image_scaled_buffer:
                            image_scaled.save(image_scaled_buffer, format="PNG")
                            print_label = image_scaled_buffer.getvalue()
                
                success = await printer.print_document(print_label)
                
                if success:
                    logger.info("shipment label printed", script=sys.argv[0])
                else:
                    logger.error("shipment label FAILED to print", script=sys.argv[0])
   
        except asyncio.CancelledError:
            break
        except (Exception, DymoPrinterError) as e:
            logger.exception("Consumer error", error=str(e), script=sys.argv[0])
            queue.task_done()
        else:
            queue.task_done()

    logger.info("Consumer finished.", script=sys.argv[0])


# Main Function
async def main() -> None:
    queue: MessageQueue[Document] = AsyncQueue(maxsize=10)
    processor: DocumentProcessor[bytes] = PdfProcessorUPSCrop()
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
