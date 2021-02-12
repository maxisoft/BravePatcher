import datetime
import json
import re
import urllib.request
from enum import Enum, auto, unique
from functools import lru_cache
from typing import Optional


@unique
class BraveChannel(Enum):
    Nightly = auto()
    Dev = auto()
    Beta = auto()
    Release = auto()


_default_release_asset_url = "https://api.github.com/repos/brave/brave-browser/releases?per_page={per_page}"


@lru_cache(512)
def _parse_github_date(d):
    return datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ")


_rc_regex = re.compile(r"^[\w\s.]+(RC\d+)\s*$", re.IGNORECASE)


def _try_get_brave_release_asset_url(name: str, url: str, per_page: int, skip_rc=True) -> Optional[str]:
    url = url.format(per_page=per_page)
    with urllib.request.urlopen(url) as f:  # nosec
        data = json.load(f)
    empty: tuple = tuple()

    for release in sorted(data, key=lambda e: _parse_github_date(e['published_at']), reverse=True):
        if skip_rc and re.match(_rc_regex, release.get("name")):
            continue
        assets = release.get('assets', empty)
        for asset in assets:
            if asset["name"] == name:
                return asset['browser_download_url']
    return None


def get_brave_release_asset_url(name='BraveBrowserStandaloneSilentSetup.exe', url=_default_release_asset_url,
                                skip_rc=True):
    for i in range(5, 10):
        res = _try_get_brave_release_asset_url(name, url, 2 ** i, skip_rc)
        if res:
            return res
    else:
        raise Exception("Unable to find release's asset")
