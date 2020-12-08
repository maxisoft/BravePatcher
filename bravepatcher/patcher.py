import base64
import datetime
import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import traceback
from dataclasses import dataclass, field, is_dataclass, asdict
from io import BytesIO, TextIOWrapper
from pathlib import Path, PurePath
from typing import List, Optional, Tuple, Union, Collection, Generator, Iterable

import appdirs
from peachpy.x86_64 import RET, XOR, TEST, rax, al, MOV, INT
from peachpy.x86_64.instructions import Instruction


class DefaultJsonEncoder(json.JSONEncoder):
    def default(self, o):
        to_json = getattr(o, 'to_json', None)
        if callable(to_json):
            return to_json()
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, (tuple, set)):
            return list(o)
        if isinstance(o, bytes):
            return base64.b64encode(o).decode()
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o.absolute())
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)

    @classmethod
    def dump(cls, obj, fp, *args, **kwargs):
        kwargs.setdefault('cls', cls)
        return json.dump(obj, fp, *args, **kwargs)

    @classmethod
    def dumps(cls, obj, *args, **kwargs):
        kwargs.setdefault('cls', cls)
        return json.dumps(obj, *args, **kwargs)


def pattern_2_re(pattern: str) -> re.Pattern:
    def gen():
        mapping = {'??': '.', '*': '.*?'}

        for i, sub in enumerate(pattern.split(' ')):
            if sub in mapping:
                yield mapping.get(sub).encode()
            elif sub.startswith('?'):
                yield b'.'
            elif sub.endswith('?'):
                base = int(sub[0], 16) * 16
                yield b'[%b-%b]' % (re.escape(base.to_bytes(1, 'little')), re.escape((base + 15).to_bytes(1, 'little')))
            else:
                yield re.escape(int(sub, 16).to_bytes(1, 'little'))

    pattern = b''.join(gen())
    return re.compile(pattern, re.DOTALL | re.ASCII)


class MemorySearchException(Exception):
    pass


class MemorySearchNotFoundException(MemorySearchException):
    pass


class MemorySearchTooManyMatchException(MemorySearchException):
    pass


class MemorySearch:
    def __init__(self, memory: bytes):
        self.memory = memory

    def find_pattern(self, pattern: str) -> re.Match:
        regex = pattern_2_re(pattern)
        res = None
        for m in re.finditer(regex, self.memory):
            if res is not None:
                raise MemorySearchTooManyMatchException("More than 1 matches")
            res = m
        if res is None:
            raise MemorySearchNotFoundException("No match")
        return res


@dataclass
class PatchedSegment:
    name: str
    pattern: dict
    original_bytes: bytes
    patched_bytes: bytes
    start_address: int

    @property
    def end_address(self) -> int:
        return self.end_address + len(self.original_bytes)


@dataclass
class PatchError:
    name: str
    pattern: str
    reason: str
    stacktrace: str


class PatchException(Exception):
    def __init__(self, patch_error: PatchError):
        self.error = patch_error

@dataclass
class PatcherResult:
    patched_bytes: bytes
    original_bytes: Optional[bytes] = None
    segments: List[PatchedSegment] = field(default_factory=list)
    errors: List[PatchError] = field(default_factory=list)

    def to_json(self):
        return {'segments': self.segments, 'errors': self.errors}


class InMemoryPatcher:
    def __init__(self, pattern_data: dict):
        self.pattern_data = pattern_data

    def patch(self, content: bytes) -> PatcherResult:
        buff = BytesIO(content)
        patch_list = [
            "patch_show_notification",
            #"patch_should_allow",
            #"patch_all_should_allow",
            #"patch_should_exclude",
            #"patch_should_pace",
            "patch_is_focus_assist_enabled",
            "patch_should_show_notifications"]

        segments = []
        errors = []
        for i, patch_name in enumerate(patch_list):
            patch_function = getattr(self, patch_name)
            try:
                l = patch_function(buff, content)
                for e in l:
                    if isinstance(e, PatchedSegment):
                        segments.append(e)
                    elif isinstance(e, PatchException):
                        errors.append(e.error)
                    else:
                        raise TypeError()
            except PatchException as e:
                errors.append(e.error)
        patched = buff.getvalue()
        return PatcherResult(patched, content, segments, errors)

    def get_pattern(self, name: str) -> Optional[dict]:
        return self.pattern_data["patterns"].get(name)

    def list_patterns(self) -> Iterable[str]:
        return self.pattern_data["patterns"].keys()

    def _search_pattern(self, pattern_name: str, content: bytes):
        pattern_info = self.get_pattern(pattern_name)
        if pattern_info is None:
            raise PatchException(PatchError(pattern_name, "", "PatternNotFound", ""))
        pattern = pattern_info["pattern"]
        try:
            search = MemorySearch(content)
            return search.find_pattern(pattern)
        except MemorySearchException as e:
            raise PatchException(PatchError(pattern_name, pattern, type(e).__name__, traceback.format_exc(limit=15)))

    def _write_instruction(self, instr: Instruction, buff: BytesIO, match: re.Match):
        return self._write_bytes(instr.encode(), buff, match)

    def _write_instructions(self, instructions: Collection[Instruction], buff: BytesIO, match: re.Match):
        encoded = BytesIO()
        for instr in instructions:
            encoded.write(instr.encode())
        return self._write_bytes(encoded.getvalue(), buff, match)

    @staticmethod
    def _write_bytes(data: bytes, buff: BytesIO, match: re.Match):
        start, end = match.span()
        if len(data) > end - start:
            raise ValueError("too many bytes to write")
        buff.seek(start)
        buff.write(data)

    def _create_patched_segment(self, name: str, buff: BytesIO, match: re.Match):
        buff.seek(match.start())
        patched_bytes = buff.read(match.end() - match.start())
        return PatchedSegment(name=name,
                              pattern=self.get_pattern(name),
                              patched_bytes=patched_bytes,
                              original_bytes=match.group(0),
                              start_address=match.start()
                              )

    def _std_patch(self, name: str, op: Union[Instruction, Collection[Instruction]], buff: BytesIO, content: bytes):
        match = self._search_pattern(name, content)
        if isinstance(op, Instruction):
            self._write_instruction(op, buff, match)
        else:
            self._write_instructions(op, buff, match)
        return [self._create_patched_segment(name, buff, match)]

    @staticmethod
    def _return_x64() -> Tuple[Instruction, ...]:
        return RET(), INT(3), INT(3), INT(3)

    @staticmethod
    def _return_0_x64() -> Tuple[Instruction, ...]:
        return XOR(rax, rax), TEST(al, al), RET(), INT(3), INT(3)

    @staticmethod
    def _return_1_x64() -> Tuple[Instruction, ...]:
        return MOV(al, 1), TEST(al, al), RET(), INT(3), INT(3), INT(3)

    def patch_show_notification(self, buff: BytesIO, content: bytes):
        return self._std_patch("AdDelivery::ShowNotification", self._return_x64(), buff, content)

    def patch_should_allow(self, buff: BytesIO, content: bytes):
        return self._std_patch("ads::ShouldAllow", self._return_1_x64(), buff, content)

    def patch_all_should_allow(self, buff: BytesIO, content: bytes):
        def gen():
            for pattern in self.list_patterns():
                if not pattern.endswith(":ShouldAllow"):
                    continue
                if pattern == "ads::ShouldAllow":
                    continue
                try:
                    match = self._search_pattern(pattern, content)
                    self._write_instructions(self._return_1_x64(), buff, match)
                    yield self._create_patched_segment(pattern, buff, match)
                except PatchException as e:
                    yield e

        return list(gen())

    def patch_should_exclude(self, buff: BytesIO, content: bytes):
        return self._std_patch("ads:ShouldExclude", self._return_0_x64(), buff, content)

    def patch_should_pace(self, buff: BytesIO, content: bytes):
        return self._std_patch("AdPacing::ShouldPace", self._return_0_x64(), buff, content)

    def patch_is_focus_assist_enabled(self, buff: BytesIO, content: bytes):
        return self._std_patch("NotificationHelperWin::IsFocusAssistEnabled", self._return_0_x64(), buff, content)

    def patch_should_show_notifications(self, buff: BytesIO, content: bytes):
        return self._std_patch("NotificationHelperWin::ShouldShowNotifications", self._return_1_x64(), buff, content)


class DataRepository:
    app_name = "BravePatcher"
    author = "Maxisoft"

    def __init__(self):
        self.data_dir = Path(appdirs.user_data_dir(self.app_name, self.author))
        self.config_dir = Path(appdirs.user_config_dir(self.app_name, self.author))

    def _create_directories(self):
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)

    @property
    def pattern_data_path(self) -> Path:
        self._create_directories()
        return Path(self.data_dir, "patterns.json")

    @property
    def chrome_backup(self):
        self._create_directories()
        return Path(self.data_dir, "chrome.dll.tar.gz")

    @property
    def chrome_backup_json(self):
        self._create_directories()
        return Path(self.data_dir, "chrome.dll.json")

    @property
    def patch_results_json(self):
        self._create_directories()
        return Path(self.data_dir, "patch_results.json")

    def create_tmp_dir(self, suffix='') -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory(prefix=self.app_name, suffix=suffix)


class Patcher:
    def __init__(self, pattern_data: dict):
        self.pattern_data = pattern_data
        self.data_repo = DataRepository()

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
            return chrome_dll.samefile(Path(path))
        return False

    def patch(self, chrome_dll: Path):
        content = chrome_dll.read_bytes()
        result = InMemoryPatcher(self.pattern_data).patch(content)

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
