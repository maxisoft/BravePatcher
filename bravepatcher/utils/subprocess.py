import os
import platform
import shlex
import subprocess
import warnings
import webbrowser
from pathlib import Path

__all__ = ['explorer_open_folder', 'check_call', 'check_output']


def check_call(cmd: str, *args, **kwargs):
    return subprocess.check_call(shlex.split(cmd), *args, **kwargs)


def check_output(cmd: str, *args, **kwargs):
    kwargs.setdefault("text", True)
    return subprocess.check_output(shlex.split(cmd), *args, **kwargs)


def _explorer_open_folder_default(folder: Path):
    webbrowser.open(str(Path(folder).absolute().as_uri()))


def _explorer_open_folder_windows(folder: Path):
    try:
        os.startfile(str(Path(folder).absolute()))
    except:
        check_call(f"start \"{Path(folder).absolute()}\"")


def _explorer_open_folder_linux(folder: Path):
    try:
        check_call(f"xdg-open \"{Path(folder).absolute()}\"")
    except:
        try:
            check_call(f"browse \"{Path(folder).absolute()}\"")
        except:
            _explorer_open_folder_default(folder)


def _explorer_open_folder_darwin(folder: Path):
    try:
        check_call(f"open \"{Path(folder).absolute()}\"")
    except:
        _explorer_open_folder_default(folder)


def explorer_open_folder(folder: Path):
    f = globals().get(f'_explorer_open_folder_{str(platform.system()).lower()}')
    if f is None:
        warnings.warn(f"unsupported system {platform.system()}")
        f = _explorer_open_folder_default
    return f(folder)
