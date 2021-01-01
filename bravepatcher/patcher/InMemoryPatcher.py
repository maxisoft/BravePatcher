import re
import traceback
from io import BytesIO
from typing import Iterable, Collection, Union, Tuple
from dataclasses import asdict

from .MemorySearch import MemorySearch
from .exceptions import *
from .models import *
from ..pattern import PatternData, Pattern
from ..static_data import X64InstructionsData, x64_instructions as default_x64_instructions


class InMemoryPatcher:
    def __init__(self, pattern_data: PatternData, x64_instructions: Optional[X64InstructionsData] = None):
        self.pattern_data = pattern_data
        self.x64_instructions = x64_instructions or default_x64_instructions

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

    def get_pattern(self, name: str) -> Optional[Pattern]:
        return self.pattern_data.patterns.get(name)

    def list_patterns(self) -> Iterable[str]:
        return self.pattern_data.patterns.keys()

    def _search_pattern(self, pattern_name: str, content: bytes) -> re.Match:
        pattern = self.get_pattern(pattern_name)
        if pattern is None:
            raise PatchException(PatchError(pattern_name, "", "PatternNotFound", ""))
        try:
            search = MemorySearch(content)
            return search.find_pattern(pattern)
        except MemorySearchException as e:
            raise PatchException(PatchError(pattern_name, pattern.pattern, type(e).__name__, traceback.format_exc(limit=15)))

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
                              pattern=asdict(self.get_pattern(name)),
                              patched_bytes=patched_bytes,
                              original_bytes=match.group(0),
                              start_address=match.start()
                              )

    def _std_patch(self, name: str, op: bytes, buff: BytesIO, content: bytes):
        match = self._search_pattern(name, content)
        self._write_bytes(op, buff, match)
        return self._create_patched_segment(name, buff, match),

    def _return_x64(self):
        return self.x64_instructions.return_nop

    def _return_0_x64(self):
        return self.x64_instructions.return_0

    def _return_1_x64(self):
        return self.x64_instructions.return_1

    def patch_show_notification(self, buff: BytesIO, content: bytes):
        return self._std_patch("AdDelivery::ShowNotification", self._return_x64(), buff, content)

    def patch_should_allow(self, buff: BytesIO, content: bytes):
        return self._std_patch("ads::ShouldAllow", self._return_1_x64(), buff, content)

    def patch_all_should_allow(self, buff: BytesIO, content: bytes):
        def gen():
            for pattern in self.list_patterns():
                if not pattern.endswith(":ShouldAllow"):
                    continue
                if pattern == "ads::ShouldAllow":  # already handled by patch_should_allow()
                    continue
                try:
                    match = self._search_pattern(pattern, content)
                    self._write_bytes(self._return_1_x64(), buff, match)
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
