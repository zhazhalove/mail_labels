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
- Python 3.10+

## Usage

### Step 1: Run the PDF File Monitor
This script watches a directory for PDF files, reads them, and sends them via ZeroMQ.
```sh
python uploader.py
```
**Behavior:**
- Monitors a designated folder (`%LOCALAPPDATA%/pdf_monitor` on Windows).
- Sends the file content over a ZeroMQ PUSH socket (`tcp://localhost:5555`).
- Deletes the file after successful transmission.

### Step 2: Run the PDF Processor
This script asynchronously receives PDFs, processes them into images, and saves them as PNGs.
```sh
python consumer_producer.py
```
**Behavior:**
- Binds to ZeroMQ PULL socket (`tcp://*:5555`).
- Converts the first page of each received PDF to a PNG image.
- Auto-crops whitespace and resizes for label printing (Dymo label format: 1228x1879 pixels).
- Saves the processed image with a dynamically generated filename.
- Prints the image label to a printer (dymo)

### Stopping the Services
Both scripts can be stopped using `Ctrl+C`.

## File Descriptions

### `uploader.py`
Monitors a directory and sends PDFs over ZeroMQ.
- Uses `watchdog` to track file changes.
- Implements retry logic for locked files.
- Deletes successfully sent files.

### `consumer_producer.py`
Receives PDFs and converts them into PNG images.
- Uses `asyncio` for non-blocking message handling.
- Processes PDFs using `pymupdf` and `Pillow`.
- Implements a producer-consumer pattern with an async queue.

## Configuration
Modify the following constants in the scripts if needed:
- **ZeroMQ Address**: Update `ZMQ_CONNECT_ADDRESS` in `uploader.py` and `consumer_producer.py`.
- **Folder**: Change `FOLDER` in `uploader.py` if necessary.
- **PNG_OUTPUT_FOLDER**: PNG output folder in `consumer_producer.py`.
- **LOG_CONFIG**: structlog logging configuration file in `uploader.py` and `consumer_producer.py`.

## Example Workflow
1. Start `uploader.py`.
2. Start `consumer_producer.py`.
3. Copy a PDF into `%LOCALAPPDATA%/pdf_monitor`.
4. The file will be detected, read, sent, processed, saved as an image, and sent to a printer.

## License
This project is licensed under the MIT License.
