import datetime
import json
import os
import platform
import re
import subprocess  # nosec
import urllib.request
import warnings
from enum import Enum, auto, unique
from functools import lru_cache
from pathlib import Path
from typing import Optional

import psutil

from bravepatcher.utils import check_output

_is_windows = platform.system() == "Windows"

if _is_windows:
    import winreg

    def _brave_reg(key=winreg.HKEY_CURRENT_USER) -> Optional[str]:
        try:
            with winreg.OpenKey(key, r"SOFTWARE\BraveSoftware\Update", 0, winreg.KEY_READ) as k:
                p = Path(winreg.QueryValueEx(k, "path")[0])
                if p.exists():
                    return str(p.parent.parent / r"Brave-Browser\Application\brave.exe")
        except FileNotFoundError:
            pass
        return None

    def _brave_default_install_folder(root="%LOCALAPPDATA%"):
        return os.path.expandvars(fr'{root}\BraveSoftware\Brave-Browser\Application\brave.exe')

    def get_brave_path() -> Optional[Path]:
        def gen():
            yield _brave_reg()
            yield _brave_reg(winreg.HKEY_LOCAL_MACHINE)
            yield _brave_default_install_folder()
            yield _brave_default_install_folder("%ProgramFiles%")
            yield _brave_default_install_folder("%ProgramFiles(x86)%")

        for path in filter(bool, gen()):
            res = Path(path)
            if res.exists():
                return res
        warnings.warn("unable to find brave")
        return None

else:
    def get_brave_path() -> Optional[Path]:
        warnings.warn(f"platform {platform.system()} maybe unsupported")
        try:
            path = check_output("which brave")
            return Path(path)
        except subprocess.CalledProcessError:
            pass
        return None


def find_chrome_dll(brave_path: Optional[Path]) -> Optional[Path]:
    res = None
    if brave_path is None:
        return res
    for p in brave_path.parent.rglob("chrome.dll"):
        if res is not None:
            warnings.warn("found more than 1 chrome.dll")
            break
        res = p
    return res


def kill_all_brave(brave_path: Path):
    brave_path = Path(brave_path)

    def gen():
        for p in psutil.process_iter(('pid', 'exe')):
            exe = p.info['exe']
            if exe and Path(exe) == brave_path:
                yield psutil.Process(p.pid)

    proc: Optional[psutil.Process] = None
    for proc in sorted(gen(), key=lambda proc: (proc.create_time(), proc.pid)):
        proc.kill()

    return proc is not None


def get_brave_for_chrome_dll(chrome_dll_path: Path):
    if not _is_windows:
        return Path()

    return chrome_dll_path.parent.parent / "brave.exe"


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
