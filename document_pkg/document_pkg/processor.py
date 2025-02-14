from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from .document import Document

T = TypeVar("T")

# Document Processor Interface
class DocumentProcessor(ABC, Generic[T]):
    @abstractmethod
    async def process(self, document: Document) -> T:
        pass
