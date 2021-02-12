from pathlib import Path
from typing import Optional

import psutil


def kill_all_brave(brave_path: Path):
    brave_path = Path(brave_path)

    def gen():
        for p in psutil.process_iter(('pid', 'exe')):
            exe = p.info['exe']
            if exe and Path(exe) == brave_path:
                yield psutil.Process(p.pid)

    proc: Optional[psutil.Process] = None
    for proc in sorted(gen(), key=lambda p: (p.create_time(), p.pid)):
        proc.kill()

    return proc is not None
