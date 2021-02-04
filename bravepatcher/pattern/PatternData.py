import datetime
from dataclasses import dataclass, field
from typing import Any, Mapping

from .Pattern import Pattern


@dataclass
class PatternData:
    patterns: Mapping[str, Pattern] = field(default_factory=dict)
    date: datetime.datetime = field(default_factory=datetime.datetime.now)
    version: str = ""
    errors: dict = field(default_factory=dict)
    program: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'PatternData':
        ret = cls()
        for k, v in data.items():
            target = getattr(ret, k)
            if k == "patterns":
                assert isinstance(target, dict)
                assert isinstance(v, dict)
                for pattern_name, pattern in v.items():
                    target[pattern_name] = Pattern.from_dict(pattern)
            elif k == "date":
                ret.date = datetime.datetime.fromisoformat(v)
            elif isinstance(target, dict):
                target.update(v)
            else:
                setattr(ret, k, v)
        return ret
