import warnings
from pathlib import Path

from .AbstractFirewallHelper import AbstractFirewallHelper


class NoOpFirewallHelper(AbstractFirewallHelper):

    def _warn(self):
        warnings.warn(f"No {type(self).__name__} supported on this platform")

    def allow_program(self, path: Path, name: str):
        self._warn()

    def block_program(self, path: Path, name: str):
        self._warn()

    def has_rule(self, name: str) -> bool:
        self._warn()
        return False
