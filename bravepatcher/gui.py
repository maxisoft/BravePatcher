#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import json
import platform
import warnings
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import BoundedSemaphore

import PySimpleGUI as sg

from bravepatcher.DataRepository import DataRepository
from bravepatcher.patcher import Patcher
from bravepatcher.pattern import PatternData
from bravepatcher.utils import explorer_open_folder
from bravepatcher.utils.brave import get_brave_path, find_chrome_dll, kill_all_brave, get_brave_for_chrome_dll

try:
    chrome_dll = find_chrome_dll(get_brave_path())
except OSError:
    chrome_dll = ""

data_repo = DataRepository()

with open("patterns_3372133802865133559.json") as f:
    data = PatternData.from_dict(json.load(f))

patcher = Patcher(data, data_repo)

chrome_dll_valid = sg.Text(" ", auto_size_text=True)
chrome_dll_in = sg.In(chrome_dll, key="chrome_dll", enable_events=True)
chrome_file_browse = sg.FileBrowse("Browse for chrome.dll", target=chrome_dll_in.Key, initial_folder=chrome_dll.parent,
                                   file_types=(("Chromium dll", "chrome.dll"), ("Any", "*")))
ok_btn = sg.Button('Patch', disabled=not Path(chrome_dll).exists(), focus=True, bind_return_key=True)
restore_btn = sg.Button('Restore', disabled=not patcher.has_backup(Path(chrome_dll)))
cancel_btn = sg.Button('Cancel', visible=False)
status_text = sg.Text(" " * 80, auto_size_text=True, key='status_text')

menu_def = [['File', ['Open Brave Folder', 'Open AppData Folder', 'Patch', 'Restore', 'Exit']],
            ['Tool', ['Start Brave', 'Stop Brave', 'Brave Update', ['Enable Updates', 'Disable Updates']]]]

safe_menu_def = [['File', ['Open Brave Folder', 'Open AppData Folder']],
                 ['Tool', ['Stop Brave', 'Brave Update', ['Enable Updates', 'Disable Updates']]]]

menu = sg.Menu(menu_def, key='menu')

layout = [
    [menu],
    [chrome_dll_valid, chrome_dll_in, chrome_file_browse],
    [sg.Checkbox("Disable ad notifications".ljust(27), default=True, key='disable_notifications',
                 tooltip='''Still a beta feature !
No more ad notifications popup while your browser keep earning BAT.
Side effect: it prevent the browser from recording the ads history.'''),
     sg.Checkbox("Disable ads limitations", default=True, key='disable_limitations',
                 tooltip='''Disable various internal checks to prevent the user to gains BAT more often.
eg 20/50 per hour/day ads limits''')],
    [sg.Checkbox("Disable random ads pace", default=False, key='disable_pace',
                 tooltip='Ads pace prevent the browser to spam ads and add more randomness'),
     sg.Checkbox("Stop Brave before patching", default=True, key='stop_brave_patch',
                 tooltip='Stop brave by yourself or tick this option to avoid errors.')],
    [sg.HorizontalSeparator()],
    [ok_btn, restore_btn, cancel_btn, status_text],
]

window = sg.Window('Brave Patcher', layout)
executor = ThreadPoolExecutor(1)
executor_lock = BoundedSemaphore(1)


def start_long_task(task, window, disable_buttons: bool = True):
    @functools.wraps(task)
    def wrapped():
        with executor_lock:
            return task()

    with executor_lock:
        if disable_buttons:
            window['Patch'].update(disabled=True)
            window['Restore'].update(disabled=True)
            window['Browse for chrome.dll'].update(disabled=True)
            window['menu'].update(safe_menu_def)

        try:
            return executor.submit(wrapped)
        except Exception:
            update_gui_state()
            raise


def build_patch_option(window: sg.Window) -> set:
    def checked(key: str):
        return window[key].get()

    patch_list = {
        "patch_is_focus_assist_enabled",
        "patch_should_show_notifications",
        "patch_initialize_toast_notifier"
    }

    if checked('disable_notifications'):
        patch_list |= {"patch_show_notification", "patch_initialize_toast_notifier"}

    if checked('disable_limitations'):
        patch_list |= {"patch_should_allow", "patch_all_should_allow", "patch_should_exclude"}

    if checked('disable_pace'):
        patch_list |= {'patch_should_pace'}

    return patch_list


def validate():
    if not Path(chrome_dll_in.get()).exists():
        return False
    return True


def update_gui_state():
    chrome_dll_valid.update("✓" if validate() else "✖")
    ok_btn.update(disabled=not validate())
    restore_btn.update(disabled=not patcher.has_backup(Path(chrome_dll_in.get())))
    chrome_file_browse.update(disabled=False)
    if menu.MenuDefinition is not menu_def:
        menu.update(menu_def)


class EventHandlerHelper:
    def __init__(self):
        self.handlers = defaultdict(list)

    def register(self, name: str, handler):
        handlers = self.handlers[name]
        handlers.append(handler)

    def dispatch(self, name, event, values, window):
        handlers = self.handlers.get(name)
        if not handlers:
            warnings.warn(f"There's no handler for event {name}")
            return 0
        count = 0
        for count, handler in enumerate(self.handlers[name]):
            handler(event, values, window)
        return count


def event_handler(name=None):
    def decorator(func):
        nonlocal name
        if name is None:
            name = str(func.__name__).replace('__main__.', '')
        from inspect import signature
        sig = signature(func)
        params = sig.parameters

        @functools.wraps(func)
        def wrapper(event, values, window, **kwargs):
            p_dict = dict()
            for k in ('event', 'values', 'window'):
                if k in params:
                    p_dict[k] = locals()[k]
            if kwargs:
                p_dict.update(kwargs)
            return func(**p_dict)

        event_handler.helper.register(name, wrapper)
        return wrapper

    return decorator


event_handler.helper = EventHandlerHelper()


def _update_status_text(window, text: str, **kwargs):
    return window.write_event_value("request_status_text_update", (text, kwargs))


update_status_text = partial(_update_status_text, window)


@event_handler("request_gui_update")
def on_request_gui_update():
    update_gui_state()


@event_handler("request_status_text_update")
def on_request_status_text_update(event, values, window):
    status_text: sg.Text = window["status_text"]
    payload = values[event]
    if len(payload) == 1:
        status_text.update(payload[0])
    else:
        assert len(payload) == 2
        status_text.update(payload[0], **payload[1])


@event_handler("chrome_dll")
def on_chrome_dll_change():
    update_gui_state()


@event_handler("request_error_display")
def on_request_error_display(event, values):
    sg.popup_error(values[event], keep_on_top=True, modal=True)


@event_handler("Patch")
def on_patch(window: sg.Window):
    update_status_text("Patching brave ...")
    should_kill_brave = window["stop_brave_patch"].get()
    chrome_dll_path = Path(window['chrome_dll'].get())
    patch_list = build_patch_option(window)

    def patch():
        try:
            if should_kill_brave:
                kill_all_brave(get_brave_for_chrome_dll(chrome_dll_path))
            patcher.patch(chrome_dll_path, patch_list)
        except Exception as e:
            update_status_text(f"✖ Failed to patch with exception {type(e).__name__}", text_color="orange")
            window.write_event_value("request_error_display", f"{e}")
        else:
            update_status_text("✅ Brave patched")
        finally:
            window.write_event_value("request_gui_update", None)

    start_long_task(patch, window)


@event_handler("Restore")
def on_restore(window: sg.Window):
    update_status_text("Restoring brave ...")
    should_kill_brave = window["stop_brave_patch"].get()
    chrome_dll_path = Path(window['chrome_dll'].get())

    def restore():
        try:
            if should_kill_brave:
                kill_all_brave(get_brave_for_chrome_dll(chrome_dll_path))
            patcher.restore_backup(chrome_dll_path)
        except Exception as e:
            window.write_event_value("request_error_display", f"{e}")
            update_status_text(f"✖ Failed to restore with exception {type(e).__name__}", text_color="orange")
        else:
            update_status_text("✅ Brave restored")
        finally:
            window.write_event_value("request_gui_update", None)

    start_long_task(restore, window)


@event_handler("Open Brave Folder")
def on_open_brave_folder(window):
    chrome_dll_path = Path(window['chrome_dll'].get())
    try:
        if platform.system() == "Windows":
            explorer_open_folder(chrome_dll_path.parent.parent)
        else:
            explorer_open_folder(chrome_dll_path.parent)
    except Exception as e:
        sg.popup_error(f"{e}", keep_on_top=True, modal=True)


@event_handler("Open AppData Folder")
def on_open_appdata_folder():
    try:
        explorer_open_folder(data_repo.data_dir)
    except Exception as e:
        sg.popup_error(f"{e}", keep_on_top=True, modal=True)


@event_handler("Start Brave")
def on_start_brave(window):
    import subprocess
    chrome_dll_path = Path(window['chrome_dll'].get())
    try:
        subprocess.Popen(str(get_brave_for_chrome_dll(chrome_dll_path)))
    except Exception as e:
        sg.popup_error(f"{e}", keep_on_top=True, modal=True)


@event_handler("Stop Brave")
def on_stop_brave(window):
    chrome_dll_path = Path(window['chrome_dll'].get())
    try:
        kill_all_brave(get_brave_for_chrome_dll(chrome_dll_path))
    except Exception as e:
        sg.popup_error(f"{e}", keep_on_top=True, modal=True)


def main():
    if platform.system() == "Windows":
        from ctypes import windll
        windll.kernel32.FreeConsole()
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel', 'Exit'):
            break

        event_handler.helper.dispatch(event, event, values, window)

    executor.shutdown(True)
    window.close()


if __name__ == '__main__':
    main()
