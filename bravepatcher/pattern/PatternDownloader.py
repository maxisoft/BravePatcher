import json
import os
import shutil
from io import BytesIO
from pathlib import PurePath
from typing import Any, Callable, Tuple, Optional
from urllib.request import urlopen
from zipfile import ZipFile, ZipInfo

from .PatternData import PatternData

__all__ = ['PatternDownloader']

_default_url = "https://github.com/maxisoft/BravePatcher/archive/pattern.zip"


def _parse_version(version: str) -> Tuple[int]:
    return tuple(map(int, version.split('.')))


def _compare_version_strings(left: str, right: str) -> Tuple[int]:
    lv, rv = _parse_version(left), _parse_version(right)
    if len(lv) < len(rv):
        lv += (0,) * (len(rv) - len(lv))
    elif len(rv) < len(lv):
        rv += (0,) * (len(lv) - len(rv))
    return tuple(int(lv[i] - rv[i]) for i in range(len(lv)))


class PatternDownloader:
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.environ.get("BRAVE_PATTERN_URL", _default_url)

    def _download_pattern_data(self, cmp: Callable[[ZipInfo], Any]) -> PatternData:
        with urlopen(self.url, timeout=15) as remote:
            buff = BytesIO()
            shutil.copyfileobj(remote, buff)
            buff.seek(0, 0)
            with ZipFile(buff) as zipfile:
                def pred(zi: ZipInfo):
                    p = PurePath(zi.filename)
                    return p.name.endswith('.json') and len(p.parents) >= 2

                most_recent = max(filter(pred, zipfile.filelist), key=cmp)
                with zipfile.open(most_recent.filename) as f:
                    return self._parse_data_to_pattern_data(f.read())

    @staticmethod
    def _parse_data_to_pattern_data(data: bytes) -> PatternData:
        return PatternData.from_dict(json.loads(data))

    def download_latest_version(self) -> PatternData:
        def compare_key(zi: ZipInfo):
            return *_parse_version(PurePath(zi.filename).stem), zi.date_time

        return self._download_pattern_data(compare_key)

    def download_for_version(self, version: str) -> PatternData:
        def compare_key(zi: ZipInfo):
            return *_compare_version_strings(PurePath(zi.filename).stem, version), zi.date_time

        return self._download_pattern_data(compare_key)
