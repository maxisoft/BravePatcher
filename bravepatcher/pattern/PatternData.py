from dataclasses import dataclass, field
from typing import Mapping, Pattern, Any

from .Pattern import Pattern


@dataclass
class PatternData:
    x64: Mapping[str, Pattern] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'PatternData':
        ret = cls()
        for k, v in data.items():
            target = getattr(ret, k)
            assert isinstance(target, dict)
            for pattern_name, pattern in v.items():
                target[pattern_name] = Pattern.from_dict(pattern)
        return ret
