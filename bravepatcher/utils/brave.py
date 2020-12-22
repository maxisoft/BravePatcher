import os
import platform
import warnings
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
                    return p.parent.parent / r"Brave-Browser\Application\brave.exe"
        except FileNotFoundError:
            pass


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
        return Path()


else:
    def get_brave_path() -> Path:
        warnings.warn(f"platform {platform.system()} maybe unsupported")
        try:
            path = check_output("which brave")
            return Path(path)
        except:
            pass
        return Path()


def find_chrome_dll(brave_path: Path) -> Path:
    res = None
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

    proc: psutil.Process
    for proc in sorted(gen(), key=lambda proc: (proc.create_time(), proc.pid)):
        proc.kill()


def get_brave_for_chrome_dll(chrome_dll_path: Path):
    if not _is_windows:
        return Path()

    return chrome_dll_path.parent.parent / "brave.exe"
