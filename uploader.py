"""
PDF File Monitor with ZeroMQ Messaging

This script monitors a specific folder for newly created or modified PDF files
and sends them over a ZeroMQ PUSH socket to a configured endpoint. The script
uses the `watchdog` library to observe filesystem changes and detect relevant
file events.

Features:
- Monitors a designated folder for new or modified PDF files.
- Attempts to open and read PDF files, retrying if they are locked.
- Sends file content via ZeroMQ PUSH socket.
- Handles file deletions by removing them from the internal tracking dictionary.
- Implements basic exception handling to manage file access errors.
- Removes the file from the folder once it has been successfully sent.

Usage:
- Run the script, and copy PDF files into the designated folder.
- The script will attempt to read and send them via ZeroMQ.

Constants:
- `ZMQ_CONNECT_ADDRESS`: Specifies the ZeroMQ address to connect to.
- `folder_path`: The directory being monitored.

To stop the script, use Ctrl+C.
"""

import os, time, zmq, structlog, logging.config, yaml, sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict

# Define the ZeroMQ bind address
ZMQ_CONNECT_ADDRESS = "tcp://localhost:5555"  # Use * for all available interfaces
FOLDER = os.path.join(os.getenv("LOCALAPPDATA"), "pdf_monitor")
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



class PDFEventProcessor(FileSystemEventHandler):
    def __init__(self, folder_path: str, socket: zmq.Socket):
        self.folder_path = folder_path
        self.socket = socket
        self.last_checked_mtimes: Dict[str, float] = {}  # Type hint for clarity

    def on_modified(self, event):  # Called when a file is modified
        self.process_file_event(event)

    def on_created(self, event):  # Handles new files as well
        self.process_file_event(event)

    def on_deleted(self, event):
        if not event.is_directory:
            filepath = event.src_path
            filename = os.path.basename(filepath)
            if filename.lower().endswith(".pdf") and filename in self.last_checked_mtimes:
                del self.last_checked_mtimes[filename]  # Remove from tracking
                logger.info("Removed tracking for deleted PDF", filename=filename, script=sys.argv[0])

    def process_file_event(self, event):
        if not event.is_directory:  # Ignore directory changes
            filepath = event.src_path
            filename = os.path.basename(filepath)  # Extract filename
            if not filename.lower().endswith(".pdf"): # Only process PDF files
                return

            try:
                mtime = os.path.getmtime(filepath)

                if filename not in self.last_checked_mtimes or mtime > self.last_checked_mtimes[filename]:
                    
                    retry_attempts = 5  # Number of times to retry opening the file

                    for attempt in range(retry_attempts):
                        try:
                            with open(filepath, "rb") as f:
                                pdf_data = f.read()
                                self.socket.send(pdf_data, zmq.NOBLOCK)
                                logger.info("Sent PDF", filename=filename, script=sys.argv[0])

                            os.remove(filepath)  # Delete the file after successful send
                            logger.info("Deleted PDF after sending", filename=filename, script=sys.argv[0])
                            break  # Successfully read the file, exit loop
                        except PermissionError as e:
                            logger.warning(
                                "File is locked, retrying",
                                filename=filename,
                                attempt=attempt + 1,
                                max_attempts=retry_attempts,
                                script=sys.argv[0]
                            )
                            time.sleep(0.5)  # Wait before retrying
                        except zmq.Again:
                             logger.warning("No receiver available, skipping", filename=filename, script=sys.argv[0])
                             break # Exit loop on other excepitons
                        except Exception as e:
                            logger.error("Error reading file", filename=filename, error=str(e), script=sys.argv[0])
                            break  # Exit loop on other exceptions

                    self.last_checked_mtimes[filename] = mtime # Update last checked time

            except OSError as e:  # Catch potential OS errors like file not found
                logger.error("Error accessing file", filename=filename, error=str(e), script=sys.argv[0])
            except Exception as e:
                logger.error("Error processing/sending file", filename=filename, error=str(e), script=sys.argv[0])


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect(ZMQ_CONNECT_ADDRESS)

    folder_path = FOLDER
    os.makedirs(folder_path, exist_ok=True) # Ensure the directory exists
    event_handler = PDFEventProcessor(folder_path=folder_path, socket=socket)
    observer = Observer()
    observer.schedule(event_handler, path=folder_path, recursive=False)  # recursive=False if you only want the main folder
    observer.start()

    try:
        logger.info("Service started", folder_path=folder_path, script=sys.argv[0])
        logger.info("Service started. Press Ctrl+C to stop.", script=sys.argv[0])

        while True:
            time.sleep(1)  # Keep the main thread alive
        
    except KeyboardInterrupt:
        logger.info("Stopping services...", script=sys.argv[0])
    finally:
        observer.stop()
        observer.join()
        socket.close()
        context.term()
        logger.info("Services stopped cleanly.", script=sys.argv[0])


if __name__ == "__main__":
    main()