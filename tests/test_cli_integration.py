import os
import sys
import shlex
import subprocess
from pathlib import Path
from typing import Tuple
import pefile
import pytest
import psutil


def _get_command() -> str:
    return os.environ.get("CLI_COMMAND", "{} -m bravepatcher".format(sys.executable.replace('\\', '/')))


def _call(cmd: str, **kwargs) -> Tuple[str, str, int]:
    cmd_split = shlex.split(cmd)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 60)
    p = subprocess.run(cmd_split, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    return p.stdout, p.stderr, p.returncode


def _call_patcher(cmd: str, **kwargs) -> Tuple[str, str, int]:
    return _call(f"{_get_command()} {cmd}", **kwargs)


class TestCliIntegration:

    def test_launch_without_args(self):
        out, err, code = _call(_get_command())
        assert code == 0
        assert err == ""
        assert out.startswith("Usage: ")
        assert "help" in out

    def test_help(self):
        out, err, code = _call_patcher("--help")
        assert code == 0
        assert err == ""
        assert out.startswith("Usage: ")
        assert "help" in out

    @pytest.mark.slow_integration_test
    def test_download_in_cwd(self, tmp_path: Path):
        out, err, code = _call_patcher("download-brave", cwd=str(tmp_path.resolve()))
        assert out.startswith("downloading")
        assert err == ""
        assert code == 0
        path = Path(tmp_path, "BraveBrowserStandaloneSilentSetup.exe")
        assert path.exists()
        pe = pefile.PE(str(path))
        assert pe.is_exe()

    @pytest.mark.slow_integration_test
    def test_download_install_patch_run_restore(self, tmp_path: Path):
        if os.environ.get("CI") != "true":
            pytest.skip("skipping CI only tests")
        _, _, code = _call_patcher("download-brave", cwd=str(tmp_path.resolve()))
        assert code == 0

        path = Path(tmp_path, "BraveBrowserStandaloneSilentSetup.exe")
        subprocess.check_call(str(path))

        out, err, code = _call_patcher("patch --show-debug-result")
        print(out)
        print(err, file=sys.stderr)
        assert "Done patching brave" in out
        assert r"""'errors': []""" in out
        assert code == 0
        from bravepatcher.utils.brave import get_brave_path
        with psutil.Popen([str(get_brave_path())] + shlex.split("--headless --bwsi")) as p:
            # start and wait 30 sec assuming there's no crash
            try:
                p.wait(30)
            except subprocess.TimeoutExpired:
                pass
            else:
                assert p.returncode == 0
            finally:
                if p.is_running():
                    p.kill()

        out, err, code = _call_patcher("restore")
        print(out)
        print(err, file=sys.stderr)
        assert code == 0









