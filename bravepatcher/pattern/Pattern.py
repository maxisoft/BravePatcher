import re
import warnings
from dataclasses import dataclass
from typing import Mapping, Any


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
            for i, sub in enumerate(pattern.split(' ')):
                mapped = mapping.get(sub, marker)
                if mapped is not marker:
                    yield mapped.encode()
                elif sub.startswith('?'):
                    yield b'.' # FIXME find a way to translate this case into a simple and performant regex
                elif sub.endswith('?'):
                    base = int(sub[0], 16) * 16
                    yield b'[%b-%b]' % (
                        re.escape(base.to_bytes(1, 'little')), re.escape((base + 15).to_bytes(1, 'little')))
                else:
                    yield re.escape(int(sub, 16).to_bytes(1, 'little'))

        pattern = b''.join(gen())
        return re.compile(pattern, re.DOTALL | re.ASCII)
