from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# Type Variable for Generics
T = TypeVar('T')

# Abstract Printer Class
class AbstractPrinter(ABC, Generic[T]):
    @abstractmethod
    def print_document(self, document: T) -> bool:
        """
        Print the given document.
        """
        pass

    @abstractmethod
    def configure_printer(self, settings: dict) -> None:
        """
        Configure the printer with the provided settings.
        """
        pass

    @abstractmethod
    def get_status(self) -> str:
        """
        Retrieve the current status of the printer.
        """
        pass