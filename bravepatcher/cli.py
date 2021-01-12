#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import shutil
import urllib.request
from urllib.parse import urlparse

import typer

from bravepatcher.DataRepository import DataRepository
from bravepatcher.patcher import Patcher
from bravepatcher.pattern import PatternData
from bravepatcher.static_data import default_pattern_data
from bravepatcher.utils.brave import *

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _get_pattern_data(file: Optional[Path] = None) -> PatternData:
    if file is not None:
        pattern_file = str(file.resolve())
    else:
        pattern_file = os.environ.get("BRAVE_PATTERN_FILE", "brave_patterns.json")
    if Path(pattern_file).exists():
        with Path(pattern_file).open('rb') as f:
            data = PatternData.from_dict(json.load(f))
    else:
        data = PatternData.from_dict(json.load(default_pattern_data()))
    return data


@app.command(short_help="Download latest Brave version")
def download_brave(name: Optional[str] = typer.Option(None, envvar="BRAVE_EXE_NAME", help="asset name"),
                   rc: bool = typer.Option(False, envvar="BRAVE_ALLOW_RC", help="allow a newer release candidate"),
                   output: Optional[Path] = typer.Argument(None, writable=True,
                                                           help="path where the file will be downloaded into")):
    if name:
        url = get_brave_release_asset_url(name, skip_rc=not rc)
    else:
        url = get_brave_release_asset_url(skip_rc=not rc)
        name = Path(urlparse(url).path).name

    typer.echo(f"downloading {url}")
    if not output:
        output = Path(".")
    if output.is_dir():
        output = Path(output, name)
    with output.open('wb') as f:
        with urllib.request.urlopen(url) as w:
            shutil.copyfileobj(w, f)


@app.command(short_help="patch Brave's chrome.dll")
def patch(chrome_dll: Optional[Path] = typer.Argument(None, exists=True, dir_okay=False, envvar="BRAVE_CHROME_DLL"),
          kill_brave: bool = typer.Option(True, help="kill any brave processes"),
          patch_show_notifications: bool = typer.Option(True,
                                                        help="no more ad notifications popup while your browser keep earning BAT"),
          pattern_file: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, envvar='BRAVE_PATTERN_FILE'),
          show_debug_result: bool = typer.Option(False, help="show internal patch result", envvar="BRAVE_DEBUG")
          ):
    data_repo = DataRepository()
    data = _get_pattern_data(pattern_file)
    patcher = Patcher(data, data_repo)
    if chrome_dll is None:
        chrome_dll = find_chrome_dll(get_brave_path())
    patch_list = {
        "patch_is_focus_assist_enabled",
        "patch_should_show_notifications",
        "patch_initialize_toast_notifier",
        "patch_should_allow",
        # "patch_all_should_allow",
        "patch_should_exclude"
    }
    if patch_show_notifications:
        patch_list |= {"patch_show_notification", "patch_initialize_toast_notifier"}

    if kill_brave and kill_all_brave(get_brave_for_chrome_dll(chrome_dll)):
        typer.echo("killed brave process")
    typer.echo("Patching brave")
    result = patcher.patch(chrome_dll, patch_list)

    if show_debug_result:
        typer.echo_via_pager(pprint.pformat(result.to_json()))
    if result.errors:
        typer.echo("Patcher got errors. Use restore command or reinstall brave", err=True)
        raise typer.Exit(1)
    else:
        typer.echo("Done patching brave")


@app.command()
def restore(chrome_dll: Optional[Path] = typer.Argument(None, exists=True, dir_okay=False, envvar="BRAVE_CHROME_DLL"),
            pattern_file: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, envvar='BRAVE_PATTERN_FILE'),
            kill_brave: bool = typer.Option(True, help="kill any brave processes")):
    data_repo = DataRepository()
    data = _get_pattern_data(pattern_file)
    if chrome_dll is None:
        chrome_dll = find_chrome_dll(get_brave_path())
    patcher = Patcher(data, data_repo)
    if kill_brave and kill_all_brave(get_brave_for_chrome_dll(chrome_dll)):
        typer.echo("Killed brave process")
    patcher.restore_backup(chrome_dll)
    typer.echo("Done restoring brave")


def main():
    return app()


if __name__ == '__main__':
    main()
