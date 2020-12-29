import datetime
import importlib
import os
import shutil
import zlib
from base64 import b64encode, b64decode
from dataclasses import asdict
from io import BytesIO
from pathlib import PurePath, Path
from typing import Tuple, Callable
from urllib.request import urlopen
from zipfile import ZipFile, ZipInfo

from peachpy.x86_64 import RET, XOR, rax, MOV
from peachpy.x86_64.instructions import Instruction

url = os.environ.get("PATTERN_URL", "https://github.com/maxisoft/BravePatcher/archive/pattern.zip")


def import_template():
    """Import the template like a thug"""
    return importlib.import_module("bravepatcher.static_data_template", "bravepatcher")


def gen_default_pattern_data() -> bytes:
    with urlopen(url) as remote:
        buff = BytesIO()
        shutil.copyfileobj(remote, buff)
        buff.seek(0, 0)
        with ZipFile(buff) as zipfile:
            def pred(zi: ZipInfo):
                p = PurePath(zi.filename)
                return p.name.endswith('.json') and len(p.parents) >= 2

            def cmp_key(zi: ZipInfo):
                return zi.date_time

            most_recent = max(filter(pred, zipfile.filelist), key=cmp_key)
            with zipfile.open(most_recent.filename) as f:
                default_pattern_data = f.read()
                return b64encode(zlib.compress(default_pattern_data))


def _return_nop_x64() -> Tuple[Instruction, ...]:
    return RET(),


def _return_0_x64() -> Tuple[Instruction, ...]:
    return XOR(rax, rax), RET()


def _return_1_x64() -> Tuple[Instruction, ...]:
    return MOV(rax, 1), RET()


def gen_x64_instructions_data():
    template = import_template()
    instr_data = template.X64InstructionsData()
    for k in asdict(instr_data).keys():
        factory: Callable[[], Tuple[Instruction, ...]] = globals().get(f'_{k}_x64')
        assert callable(factory)
        instructions = factory()
        encoded = BytesIO()
        for instr in instructions:
            assert isinstance(instr, Instruction)
            encoded.write(instr.encode())
        setattr(instr_data, k, encoded.getvalue())

    return instr_data


def test_generated_template(template, real_path: Path):
    module_compiled = compile(template, str(real_path), 'exec')
    fake_globals = dict()
    fake_locals = dict()
    exec(module_compiled, fake_globals, fake_locals)
    assert "x64_instructions" in fake_locals
    assert callable(fake_locals["default_pattern_data"])
    b64decode(fake_locals["_default_pattern_data"])


if __name__ == '__main__':
    template_module = import_template()
    instr_data = gen_x64_instructions_data()
    pattern_data = gen_default_pattern_data()

    template = Path(template_module.__file__).read_text()
    template = template.replace('%PATTERN_PLACEHOLDER%', pattern_data.decode('ascii'))

    template += "\n" + "x64_instructions = " + repr(instr_data) + "\n" + \
                "gen_date = " + repr(datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat())

    template_module = import_template()
    real_path: Path = Path(template_module.__file__)
    real_path = real_path.with_name(real_path.name.replace('_template.py', '.py'))

    test_generated_template(template, real_path)
    real_path.write_text(template)
