# PDF File Monitor & Processor

This repository contains two Python scripts that implement a ZeroMQ-based system for monitoring, processing, and printing PDF files.

## Overview

### Components

1. **`uploader.py`**: Monitors a designated folder for new or modified PDF files and sends them over a ZeroMQ PUSH socket.
2. **`consumer_producer.py`**: Receives and processes PDF files asynchronously, extracting relevant portions and optionally printing them to a Dymo printer.

## Features

### `uploader.py`

- Watches a folder (`%LOCALAPPDATA%/pdf_monitor`) for newly added or modified PDF files.
- Reads PDF content and sends it via a ZeroMQ PUSH socket.
- Retries file access if the PDF is locked.
- Deletes successfully processed files.
- Logs events using `structlog`.

### `consumer_producer.py`

- Implements a producer-consumer pattern using `asyncio` and `ZeroMQ`.
- Processes received PDFs, extracting relevant regions using OpenCV.
- Converts PDF pages to images using `PyMuPDF` (`fitz`).
- Saves cropped images as PNG files.
- Optionally prints the processed output to a Dymo printer.
- Gracefully handles shutdown and errors.

## Installation

### Prerequisites

Ensure you have the following installed:

- Python 3.10+
- `pip` package manager
- Required dependencies (listed below)

### Dependencies

Install dependencies using:

```PowerShell
pip install -r requirements.txt
```

Dependencies include:

- `watchdog` (for monitoring file system events)
- `zmq` and `zmq.asyncio` (for ZeroMQ messaging)
- `structlog` (for structured logging)
- `PyMuPDF` (`fitz`) (for PDF processing)
- `Pillow` (for image handling)
- `opencv-python` (for contour detection)
- `pyyaml` (for logging configuration)
- `pywin32` (for Windows printer handling)
- `opencv_greatest_contour` (tools to extract a shipping label from a pdf)

## Usage

### Running the Uploader

This script monitors a folder for PDFs and sends them over ZeroMQ.

```PowerShell
python uploader.py
```

### Running the Consumer-Producer

This script receives, processes, and optionally prints PDFs.

```PowerShell
python consumer_producer.py
```

### Folder Path for PDFs

The uploader watches:

- **Windows**: `%LOCALAPPDATA%\pdf_monitor`

### Configuring Logging

Logging settings are defined in `logging_config.yaml`. You can adjust verbosity, format, and log file locations.

## How It Works

1. `uploader.py` detects new PDFs and sends them via ZeroMQ.
2. `consumer_producer.py` receives the PDFs, extracts useful regions, and saves them as PNGs.
3. Optionally, the processed PNG can be sent to a Dymo printer.
4. The system runs asynchronously with structured logging and error handling.

## Customization

- **Change the monitored folder**: Modify `FOLDER` in `uploader.py`.
- **Change the ZeroMQ address**: Update `ZMQ_CONNECT_ADDRESS` in both scripts.
- **Enable printing**: Uncomment the Dymo printing section in `consumer_producer.py` and configure the correct printer name.

## Error Handling

- If a PDF is locked, the uploader retries access before skipping it.
- If no receiver is available, the uploader logs a warning and skips the file.
- Processing failures in the consumer log an error but do not halt execution.
- Graceful shutdown is implemented for clean exits.

## License

This project is licensed under the MIT License.
