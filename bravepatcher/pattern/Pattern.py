import re
import warnings
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class Pattern:
    id: str = ""
    name: str = ""
    pattern: str = ""
    callingConvention: str = "unknown"
    entryPoint: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'Pattern':
        ret = cls()
        marker = object()
        for k, v in data.items():
            attr = getattr(ret, k, marker)
            if attr is not marker:
                setattr(ret, k, v)
            else:
                warnings.warn(f"found unknown {k} attribute")
        return ret

    def to_regex(self) -> re.Pattern:
        pattern = self.pattern

        def gen():
            mapping = {'??': '.', '*': '.*?'}
            marker = object()
            for sub in pattern.split(' '):
                mapped = mapping.get(sub, marker)
                if mapped is not marker:
                    yield mapped.encode()
                elif sub.startswith('?'):
                    yield b'.'
                elif sub.endswith('?'):
                    base = int(sub[0], 16) * 16
                    yield b'[%b-%b]' % (
                        re.escape(base.to_bytes(1, 'little')), re.escape((base + 15).to_bytes(1, 'little')))
                else:
                    yield re.escape(int(sub, 16).to_bytes(1, 'little'))

        pattern_tmp = b''.join(gen())
        return re.compile(pattern_tmp, re.DOTALL | re.ASCII)
