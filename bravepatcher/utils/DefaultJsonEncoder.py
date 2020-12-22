import base64
import datetime
import json
from dataclasses import is_dataclass, asdict
from pathlib import Path, PurePath


class DefaultJsonEncoder(json.JSONEncoder):
    def default(self, o):
        to_json = getattr(o, 'to_json', None)
        if callable(to_json):
            return to_json()
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, (tuple, set)):
            return list(o)
        if isinstance(o, bytes):
            return base64.b64encode(o).decode()
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o.absolute())
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)

    @classmethod
    def dump(cls, obj, fp, *args, **kwargs):
        kwargs.setdefault('cls', cls)
        return json.dump(obj, fp, *args, **kwargs)

    @classmethod
    def dumps(cls, obj, *args, **kwargs):
        kwargs.setdefault('cls', cls)
        return json.dumps(obj, *args, **kwargs)