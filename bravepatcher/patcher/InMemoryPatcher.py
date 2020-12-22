import re
import traceback
from io import BytesIO
from typing import Optional, Iterable, Collection, Union, Tuple

from peachpy.x86_64 import RET, XOR, rax, MOV
from peachpy.x86_64.instructions import Instruction

from .exceptions import *
from .models import *
from .MemorySearch import MemorySearch


class InMemoryPatcher:
    def __init__(self, pattern_data: dict):
        self.pattern_data = pattern_data

    def patch(self, content: bytes, patch_list=None) -> PatcherResult:
        buff = BytesIO(content)
        if patch_list is None:
            patch_list = [
                # "patch_show_notification",
                "patch_should_allow",
                "patch_all_should_allow",
                "patch_should_exclude",
                # "patch_should_pace",
                "patch_is_focus_assist_enabled",
                # "patch_should_show_notifications",
                "patch_initialize_toast_notifier"
            ]

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

    def _search_pattern(self, pattern_name: str, content: bytes) -> re.Match:
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

    def _write_instructions(self, instructions: Collection[Instruction], buff: BytesIO, match: re.Match,
                            offset: int = 0):
        encoded = BytesIO()
        for instr in instructions:
            encoded.write(instr.encode())
        return self._write_bytes(encoded.getvalue(), buff, match, offset)

    @staticmethod
    def _write_bytes(data: bytes, buff: BytesIO, match: re.Match, offset: int = 0):
        start, end = match.span()
        start += offset
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
        return self._create_patched_segment(name, buff, match),

    @staticmethod
    def _return_x64() -> Tuple[Instruction, ...]:
        return RET(),

    @staticmethod
    def _return_0_x64() -> Tuple[Instruction, ...]:
        return XOR(rax, rax), RET()

    @staticmethod
    def _return_1_x64() -> Tuple[Instruction, ...]:
        return MOV(rax, 1), RET()

    def patch_show_notification(self, buff: BytesIO, content: bytes):
        return self._std_patch("AdDelivery::ShowNotification", self._return_x64(), buff, content)

    def patch_should_allow(self, buff: BytesIO, content: bytes):
        return self._std_patch("ads::ShouldAllow", self._return_1_x64(), buff, content)

    def patch_all_should_allow(self, buff: BytesIO, content: bytes):
        def gen():
            for pattern in self.list_patterns():
                if not pattern.endswith(":ShouldAllow"):
                    continue
                if pattern == "ads::ShouldAllow": # already handled by patch_should_allow()
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

    def patch_initialize_toast_notifier(self, buff: BytesIO, content: bytes):
        return self._std_patch("NotificationHelperWin::InitializeToastNotifier", self._return_0_x64(), buff, content)