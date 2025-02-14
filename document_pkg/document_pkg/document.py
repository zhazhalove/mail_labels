import time
import uuid

# Document Representation
class Document:
    def __init__(self, content: bytes, filename: str = None):
        self.content: bytes = content
        self.filename: str = filename or f"document_{time.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4()}"
