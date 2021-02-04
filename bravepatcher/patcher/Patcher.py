import datetime
import hashlib
import json
import shutil
import tarfile
import tempfile
from io import BytesIO, TextIOWrapper
from pathlib import Path
from typing import Optional, Tuple

from ..DataRepository import DataRepository
from ..pattern import PatternData
from ..utils.DefaultJsonEncoder import DefaultJsonEncoder
from .InMemoryPatcher import InMemoryPatcher


class Patcher:
    def __init__(self, pattern_data: PatternData, data_repo: Optional[DataRepository] = None):
        self.pattern_data = pattern_data
        self.data_repo = data_repo or DataRepository()

    @staticmethod
    def _build_chrome_info(chrome_dll: Path, content: bytes) -> dict:
        stat = chrome_dll.stat()
        return {
            'path': chrome_dll,
            'date': datetime.datetime.now(),
            'sha256': hashlib.sha256(content).hexdigest(),
            'blake2b': hashlib.blake2b(content).hexdigest(),
            'st_atime': stat.st_atime,
            'st_ctime': stat.st_ctime,
            'st_size': stat.st_size,
            'st_mtime': stat.st_mtime,
            'version': 1
        }

    @staticmethod
    def _write_chrome_info(chrome_info: dict, tar: tarfile.TarFile, stat):
        fileobj = BytesIO()
        file_str_io = TextIOWrapper(fileobj)
        DefaultJsonEncoder.dump(chrome_info, file_str_io)
        file_str_io.flush()
        fileobj.name = "chrome.dll.json"
        tarinfo = tar.tarinfo(name=fileobj.name)
        tarinfo.type = tarfile.REGTYPE
        tarinfo.size = fileobj.tell()
        tarinfo.mtime = stat.st_mtime
        fileobj.seek(0)
        tar.addfile(tarinfo, fileobj=fileobj)

    def create_tmp_backup(self, chrome_dll: Path, content: bytes) -> Tuple[tempfile.TemporaryDirectory, Path, dict]:
        tmp = self.data_repo.create_tmp_dir('chrome_backup')
        try:
            path = Path(tmp.name, 'chrome.dll.tar.gz')
            with tarfile.open(str(path), 'w:gz') as tar:
                chrome_info = self._build_chrome_info(chrome_dll, content)
                self._write_chrome_info(chrome_info, tar, chrome_dll.stat())
                tar.add(str(chrome_dll), "chrome.dll")
            return tmp, path, chrome_info
        except Exception:
            tmp.cleanup()
            raise

    def has_backup(self, chrome_dll: Path):
        if self.data_repo.chrome_backup.exists() and self.data_repo.chrome_backup_json.exists():
            chrome_info = json.loads(self.data_repo.chrome_backup_json.read_text())
            path = chrome_info.get('path', '')
            return chrome_dll.exists() and Path(path).exists() and chrome_dll.samefile(Path(path))
        return False

    def restore_backup(self, chrome_dll: Path):
        with tarfile.open(str(self.data_repo.chrome_backup)) as tar:
            with self.data_repo.create_tmp_dir('extract') as tmp:
                tar.extractall(tmp)
                file = next(Path(tmp).rglob(chrome_dll.name))
                shutil.move(file, str(chrome_dll))

    def patch(self, chrome_dll: Path, patch_option=None):
        content = chrome_dll.read_bytes()
        result = InMemoryPatcher(self.pattern_data).patch(content, patch_option)

        def apply_patch():
            self.data_repo.patch_results_json.write_text(DefaultJsonEncoder.dumps(result))
            with chrome_dll.open('wb') as dll:
                dll.write(result.patched_bytes)

        self.data_repo.pattern_data_path.write_text(DefaultJsonEncoder.dumps(self.pattern_data))
        if not self.has_backup(chrome_dll):
            tmp, tar_path, chrome_info = self.create_tmp_backup(chrome_dll, content)
            with tmp:
                apply_patch()
                self.data_repo.chrome_backup_json.write_text(DefaultJsonEncoder.dumps(chrome_info))
                shutil.move(tar_path, self.data_repo.chrome_backup)
        else:
            apply_patch()

        return result
