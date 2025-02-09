"""
This script demonstrates asynchronous processing of PDF documents using asyncio,
zeromq for message passing, and a process pool to handle blocking PDF operations.
It implements a producer-consumer pattern with improved error handling and shutdown.
"""

import zmq, zmq.asyncio, asyncio, time, fitz, io
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageChops
from pathlib import Path


PNG_OUTPUT_FOLDER = Path("output_png")
PNG_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Type Variable for Generics
T = TypeVar('T')

# Document Representation
class Document:
    def __init__(self, content: bytes, filename: str = None):
        self.content: bytes = content
        self.filename: str = filename or f"document_{time.strftime('%Y%m%d%H%M%S')}"  # Dynamic filename

# Document Processor Interface
class DocumentProcessor(ABC, Generic[T]):
    @abstractmethod
    async def process(self, document: Document) -> T:
        pass

# PDF Processor Implementation
class PdfProcessor(DocumentProcessor[bytes]):
    def __init__(self):
        self.executor = ProcessPoolExecutor()

    async def process(self, document: Document) -> bytes:
        try:
            pdf_data = document.content
            loop = asyncio.get_running_loop()
            img_bytes = await loop.run_in_executor(self.executor, PdfProcessor.Process_pdf_sync, pdf_data)
            return img_bytes
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return None  # Return None on error


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
                    print("Error: PDF document is empty.")
                    return None
        except Exception as e:
            print(f"Error in Process_pdf_sync: {e}")
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
            print(f"Producer received and added: {document.filename}")
        except zmq.Again:
            await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Producer error: {e}")
    print("Producer finished.")


# Consumer
async def consumer(queue: MessageQueue[Document], processor: DocumentProcessor[bytes], shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set() or not queue.empty():
        try:
            document: Document = await queue.get()
            print(f"Consumer processing: {document.filename}")
            result: bytes = await processor.process(document)
            if result:
                output_filename = PNG_OUTPUT_FOLDER.joinpath(f"{document.filename}.png")
                with open(output_filename, "wb") as f:
                    f.write(result)
                print(f"Consumer processed and saved image to {output_filename}.")
            else:
                print(f"Processing failed for document: {document.filename}")
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Consumer error: {e}")
            queue.task_done()
    print("Consumer finished.")


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
        print("Service started. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(10)  # Simulate some work
            # raise KeyboardInterrupt  # Force interrupt for testing
    except KeyboardInterrupt:
        print("Service interrupted. Shutting down...")
        shutdown_event.set()  # Signal shutdown

        await queue.join()  # Wait for queue to be empty

        # Gracefully cancel tasks with a timeout
        done, pending = await asyncio.wait([producer_task, consumer_task], timeout=2.0)

        for task in pending:
            task.cancel()
            try:
                await task  # Wait for task to actually cancel (or raise CancelledError)
            except asyncio.CancelledError:
                pass

    finally:
        socket.close()
        context.term()
        print("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
        # asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        print("Service interrupted. Exiting gracefully...")
