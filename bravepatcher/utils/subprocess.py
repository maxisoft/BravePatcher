import os
import platform
import shlex
import subprocess  # nosec
import warnings
import webbrowser
from pathlib import Path

__all__ = ['open_folder_in_explorer', 'check_call', 'check_output']


def check_call(cmd: str, *args, **kwargs):
    return subprocess.check_call(shlex.split(cmd), *args, **kwargs)  # nosec


def check_output(cmd: str, *args, **kwargs):
    kwargs.setdefault("text", True)
    return subprocess.check_output(shlex.split(cmd), *args, **kwargs)  # nosec


def _open_folder_in_explorer_default(folder: Path):
    webbrowser.open(str(Path(folder).absolute().as_uri()))


def _open_folder_in_explorer_windows(folder: Path):
    try:
        os.startfile(str(Path(folder).absolute()))  # nosec
    except subprocess.CalledProcessError:
        check_call(f"start \"{Path(folder).absolute()}\"")


def _open_folder_in_explorer_linux(folder: Path):
    try:
        check_call(f"xdg-open \"{Path(folder).absolute()}\"")
    except subprocess.CalledProcessError:
        try:
            check_call(f"browse \"{Path(folder).absolute()}\"")
        except subprocess.CalledProcessError:
            _open_folder_in_explorer_default(folder)


def _open_folder_in_explorer_darwin(folder: Path):
    try:
        check_call(f"open \"{Path(folder).absolute()}\"")
    except subprocess.CalledProcessError:
        _open_folder_in_explorer_default(folder)


def open_folder_in_explorer(folder: Path):
    f = globals().get(f'_open_folder_in_explorer_{str(platform.system()).lower()}')
    if f is None:
        warnings.warn(f"unsupported system {platform.system()}")
        f = _open_folder_in_explorer_default
    return f(folder)
