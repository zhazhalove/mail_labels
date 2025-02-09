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

Usage:
- Run the script, and copy PDF files into the designated folder.
- The script will attempt to read and send them via ZeroMQ.

Constants:
- `ZMQ_CONNECT_ADDRESS`: Specifies the ZeroMQ address to connect to.
- `folder_path`: The directory being monitored.

To stop the script, use Ctrl+C.
"""

import os, time, zmq
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict

# Define the ZeroMQ bind address
ZMQ_CONNECT_ADDRESS = "tcp://localhost:5555"  # Use * for all available interfaces
FOLDER = os.path.join(os.getenv("LOCALAPPDATA"), "pdf_monitor")

class MyEventHandler(FileSystemEventHandler):
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
                print(f"Removed tracking for deleted PDF: {filename}")

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
                                print(f"Sent PDF: {filename}")

                            break  # Successfully read the file, exit loop
                        except PermissionError as e:
                            print(f"Attempt {attempt + 1}/{retry_attempts} - File is locked: {filename}. Retrying in 0.5s...")
                            time.sleep(0.5)  # Wait before retrying
                        except zmq.Again:
                             print(f"Warning: No receiver available. Skipping PDF: {filename}")
                             break # Exit loop on other excepitons
                        except Exception as e:
                            print(f"Error reading file {filename}: {e}")
                            break  # Exit loop on other exceptions

                    self.last_checked_mtimes[filename] = mtime # Update last checked time

            except OSError as e:  # Catch potential OS errors like file not found
                print(f"Error accessing file {filename}: {e}")
            except Exception as e:
                print(f"Error processing/sending file {filename}: {e}")


def main() -> None:
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect(ZMQ_CONNECT_ADDRESS)

    folder_path = FOLDER
    os.makedirs(folder_path, exist_ok=True) # Ensure the directory exists
    event_handler = MyEventHandler(folder_path=folder_path, socket=socket)
    observer = Observer()
    observer.schedule(event_handler, path=folder_path, recursive=False)  # recursive=False if you only want the main folder
    observer.start()

    try:
        print(f"copy shipment labels to: {folder_path}")
        print("Service started. Press Ctrl+C to stop.")

        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    socket.close()
    context.term()


if __name__ == "__main__":
    main()