# flake8: noqa
from base64 import b64decode
from dataclasses import dataclass
from io import BytesIO
from zlib import decompress


_default_pattern_data = b"%PATTERN_PLACEHOLDER%"

default_pattern_data_cache = None


def default_pattern_data() -> BytesIO:
    global default_pattern_data_cache
    if default_pattern_data_cache is None:
        data = b64decode(_default_pattern_data)
        default_pattern_data_cache = decompress(data)
    return BytesIO(default_pattern_data_cache)


@dataclass
class X64InstructionsData:
    return_nop: bytes = b''
    return_1: bytes = b''
    return_0: bytes = b''
