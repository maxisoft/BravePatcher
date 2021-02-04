from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PatchedSegment:
    name: str
    pattern: dict
    original_bytes: bytes
    patched_bytes: bytes
    start_address: int

    @property
    def end_address(self) -> int:
        return self.end_address + len(self.original_bytes)


@dataclass
class PatchError:
    name: str
    pattern: str
    reason: str
    stacktrace: str


@dataclass
class PatcherResult:
    patched_bytes: bytes
    original_bytes: Optional[bytes] = None
    segments: List[PatchedSegment] = field(default_factory=list)
    errors: List[PatchError] = field(default_factory=list)

    def to_json(self):
        return {'segments': self.segments, 'errors': self.errors}
