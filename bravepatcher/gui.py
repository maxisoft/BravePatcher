import os
import platform
import warnings
import json
from pathlib import Path
from typing import Optional

import PySimpleGUI as sg

from bravepatcher.patcher import Patcher

if platform.system() == "Windows":
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
        return Path()


def find_chrome_dll(brave_path: Path) -> Path:
    res = None
    for p in brave_path.parent.rglob("chrome.dll"):
        if res is not None:
            warnings.warn("found more than 1 chrome.dll")
        res = p
    return res


print(get_brave_path())
try:
    chrome_dll = find_chrome_dll(get_brave_path())
except OSError:
    chrome_dll = ""

with open("patterns_3371496867352830167.json") as f:
    data = json.load(f)


chrome_dll_in = sg.In(chrome_dll, key="chrome_dll", enable_events=True)
chrome_file_browse = sg.FileBrowse("Browse for chrome.dll", target=chrome_dll_in.Key, initial_folder=chrome_dll.parent,
                                   file_types=(("Chromium dll", "chrome.dll"), ("Any", "*")))
ok_btn = sg.Button('Ok', disabled=not Path(chrome_dll).exists(), focus=True, bind_return_key=True)
cancel_btn = sg.Button('Cancel')

def build_options() -> list:
    pass

layout = [
    [chrome_dll_in, chrome_file_browse],
    [sg.HorizontalSeparator()],
    [ok_btn, cancel_btn],
]

window = sg.Window('Brave Patcher', layout)


def validate():
    if not Path(chrome_dll_in.get()).exists():
        return False
    return True


while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
        break
    if event == "chrome_dll":
        ok_btn.update(disabled=not validate())
    if event == "Ok":
        Patcher(data).patch(Path(chrome_dll_in.get()))
    print('You entered ', values)

window.close()
