"""
This script monitors a specified folder for changes in PDF files. When a PDF file is 
modified or created, it reads the file content and sends it over a ZeroMQ PUSH socket.

**Building and Running:**

1. **Prerequisites:**
    - Python 3.6 or higher is recommended.
    - Install the required packages:
      ```bash
      pip install pyzmq watchdog
      ```

2. **Script Configuration:**
    - Save the code as a Python file (e.g., `pdf_monitor.py`).
    - Modify the `folder_path` variable in the `main` function to point to the 
      directory you want to monitor. For example:
      ```python
      folder_path="/path/to/your/pdf/folder"  # Replace with your actual path
      ```
    - The `ZMQ_BIND_ADDRESS` constant defines the ZeroMQ socket address. You can change it if needed.

3. **Running the Script (Producer):**
    - Execute the script from your terminal:
      ```bash
      python pdf_monitor.py
      ```
    - This will start the folder monitoring process and bind the ZeroMQ socket.

4. **Running a Consumer (Receiver - separate script):**
   - You'll need a separate script (e.g., `pdf_receiver.py`) to receive the PDF data. See the example below.

5. **Testing:**
    - Place or create PDF files in the monitored folder.
    - Modify an existing PDF file in the folder.
    - The `pdf_monitor.py` script will detect the changes and send the PDF data 
      through the ZeroMQ socket.
    - The `pdf_receiver.py` script will receive the data and save it. You should see the "Received and saved PDF." message.

**Important Notes:**

- The receiver script must be running *before* the producer script, as the producer binds the socket. 
- Make sure the `ZMQ_BIND_ADDRESS` is the same in both scripts.
- This example receiver simply saves the PDF to a file. You can modify it to perform other actions with the received PDF data.
- Error handling is included to make the script more robust.
- The `recursive=False` argument in `observer.schedule` means that only the top-level folder is monitored. Subfolders are not monitored. Change this to `recursive=True` if you need to monitor subfolders as well.
"""

import os
import time
import zmq
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict

# Define the ZeroMQ bind address
ZMQ_CONNECT_ADDRESS = "tcp://localhost:5555"  # Use * for all available interfaces

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

    folder_path = os.path.join(os.getenv("LOCALAPPDATA"), "pdf_monitor")
    print(f"copy shipment labels to: {folder_path}")
    os.makedirs(folder_path, exist_ok=True) # Ensure the directory exists
    event_handler = MyEventHandler(folder_path=folder_path, socket=socket)
    observer = Observer()
    observer.schedule(event_handler, path=folder_path, recursive=False)  # recursive=False if you only want the main folder
    observer.start()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    socket.close()
    context.term()


if __name__ == "__main__":
    main()