import re

from .exceptions import *


def _pattern_2_re(pattern: str) -> re.Pattern:
    def gen():
        mapping = {'??': '.', '*': '.*?'}

        for i, sub in enumerate(pattern.split(' ')):
            if sub in mapping:
                yield mapping.get(sub).encode()
            elif sub.startswith('?'):
                yield b'.'
            elif sub.endswith('?'):
                base = int(sub[0], 16) * 16
                yield b'[%b-%b]' % (re.escape(base.to_bytes(1, 'little')), re.escape((base + 15).to_bytes(1, 'little')))
            else:
                yield re.escape(int(sub, 16).to_bytes(1, 'little'))

    pattern = b''.join(gen())
    return re.compile(pattern, re.DOTALL | re.ASCII)


class MemorySearch:
    def __init__(self, memory: bytes):
        self.memory = memory

    def find_pattern(self, pattern: str) -> re.Match:
        regex = _pattern_2_re(pattern)
        res = None
        for m in re.finditer(regex, self.memory):
            if res is not None:
                raise MemorySearchTooManyMatchException("More than 1 matches")
            res = m
        if res is None:
            raise MemorySearchNotFoundException("No match")
        return res