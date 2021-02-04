import re

from ..pattern.Pattern import Pattern
from .exceptions import (MemorySearchNotFoundException,
                         MemorySearchTooManyMatchException)


class MemorySearch:
    def __init__(self, memory: bytes):
        self.memory = memory

    def find_pattern(self, pattern: Pattern) -> re.Match:
        regex = pattern.to_regex()
        res = None
        for m in re.finditer(regex, self.memory):
            if res is not None:
                raise MemorySearchTooManyMatchException("More than 1 matches")
            res = m
        if res is None:
            raise MemorySearchNotFoundException("No match")
        return res
