from abc import ABC, abstractmethod
from typing import Any, Dict

class Analyzer(ABC):
    @abstractmethod
    def analyze(self, file: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file and return results."""
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__
