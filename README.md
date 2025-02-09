# PDF File Monitor with ZeroMQ Messaging

## Overview
This repository contains two Python scripts that work together to monitor a directory for PDF files, send them over a ZeroMQ messaging system, and process them asynchronously.

### Features
- **File Monitoring**: Watches a specific folder for new or modified PDF files.
- **ZeroMQ Messaging**: Uses ZeroMQ PUSH-PULL sockets for inter-process communication.
- **Automatic File Handling**: Reads, processes, and deletes PDFs after successful transmission.
- **Asynchronous Processing**: Leverages asyncio for non-blocking message handling and PDF conversion.
- **Image Conversion**: Converts PDFs to PNG images with auto-cropping and resizing.
- **Resilient Error Handling**: Retries locked files and gracefully handles errors.

## Installation
### Prerequisites
Ensure you have the following installed:
- Python 3.8+
- `pip` for package management

### Required Python Packages
Install the required dependencies using:
```sh
pip install watchdog pyzmq pymupdf pillow
```

## Usage

### Step 1: Run the PDF File Monitor
This script watches a directory for PDF files, reads them, and sends them via ZeroMQ.
```sh
python pdf_monitor.py
```
**Behavior:**
- Monitors a designated folder (`%LOCALAPPDATA%/pdf_monitor` on Windows).
- Sends the file content over a ZeroMQ PUSH socket (`tcp://localhost:5555`).
- Deletes the file after successful transmission.

### Step 2: Run the PDF Processor
This script asynchronously receives PDFs, processes them into images, and saves them as PNGs.
```sh
python pdf_processor.py
```
**Behavior:**
- Binds to ZeroMQ PULL socket (`tcp://*:5555`).
- Converts the first page of each received PDF to a PNG image.
- Auto-crops whitespace and resizes for label printing (Dymo label format: 1228x1879 pixels).
- Saves the processed image with a dynamically generated filename.

### Stopping the Services
Both scripts can be stopped using `Ctrl+C`.

## File Descriptions

### `pdf_monitor.py`
Monitors a directory and sends PDFs over ZeroMQ.
- Uses `watchdog` to track file changes.
- Implements retry logic for locked files.
- Deletes successfully sent files.

### `pdf_processor.py`
Receives PDFs and converts them into PNG images.
- Uses `asyncio` for non-blocking message handling.
- Processes PDFs using `pymupdf` and `Pillow`.
- Implements a producer-consumer pattern with an async queue.

## Configuration
Modify the following constants in the scripts if needed:
- **ZeroMQ Address**: Update `ZMQ_CONNECT_ADDRESS` in `pdf_monitor.py` and `pdf_processor.py`.
- **Folder Path**: Change `FOLDER` in `pdf_monitor.py` if necessary.

## Example Workflow
1. Start `pdf_processor.py`.
2. Start `pdf_monitor.py`.
3. Copy a PDF into `%LOCALAPPDATA%/pdf_monitor`.
4. The file will be detected, read, sent, processed, and saved as an image.

## License
This project is licensed under the MIT License.
