import ctypes
import os
import platform
import shlex
import subprocess
from pathlib import Path

from .AbstractFirewallHelper import AbstractFirewallHelper

if platform.system() == "Windows":
    def quote(s):
        if not s:
            return '""'
        tmp = shlex.quote(s)
        if tmp[0] == "'" and tmp[-1] == "'" and tmp[0] != s[0] and tmp[-1] != s[-1]:
            return '"' + tmp[1:-1] + '"'
        return tmp

    class WindowsFirewallHelper(AbstractFirewallHelper):
        @property
        def netsh_path(self):
            return Path(os.path.expandvars(r'%WINDIR%\system32'), "netsh.exe")

        @classmethod
        def _start_as_admin(cls, program: Path, *args):
            res = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(program.resolve()), " ".join(args), None, 1)
            if res <= 32:
                raise WindowsError("unable to start as admin")

        def allow_program(self, path: Path, name: str):
            args = f'advfirewall firewall delete rule name={quote(name)}'
            self._start_as_admin(self.netsh_path, *args.split(" "))

        def block_program(self, path: Path, name: str):
            args = f'advfirewall firewall add rule name={quote(name)}' \
                   f' dir=out action=block enable=yes program={quote(str(path.resolve()))}'
            self._start_as_admin(self.netsh_path, *args.split(" "))

        def has_rule(self, name: str) -> bool:
            args = f'advfirewall firewall show rule name={quote(name)}'
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return subprocess.call([self.netsh_path.resolve()] + shlex.split(args),
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   startupinfo=si) == 0
else:
    from .NoOpFirewallHelper import NoOpFirewallHelper

    class WindowsFirewallHelper(NoOpFirewallHelper):  # type: ignore
        pass
