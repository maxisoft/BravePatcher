from abc import ABC, abstractmethod
from pathlib import Path


class AbstractFirewallHelper(ABC):
    @abstractmethod
    def allow_program(self, path: Path, name: str):
        pass

    @abstractmethod
    def block_program(self, path: Path, name: str):
        pass

    @abstractmethod
    def has_rule(self, name: str) -> bool:
        pass
