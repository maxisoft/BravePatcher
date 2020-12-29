from base64 import b64decode
from dataclasses import *
from io import BytesIO
from zlib import decompress

_default_pattern_data = b"%PATTERN_PLACEHOLDER%"


def default_pattern_data() -> BytesIO:
    if default_pattern_data.cache is None:
        data = b64decode(_default_pattern_data)
        default_pattern_data.cache = decompress(data)
    return BytesIO(default_pattern_data.cache)


default_pattern_data.cache = None


@dataclass
class X64InstructionsData:
    return_nop: bytes = b''
    return_1: bytes = b''
    return_0: bytes = b''
