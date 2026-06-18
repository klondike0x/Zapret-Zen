# -*- mode: python ; coding: utf-8 -*-

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH).resolve().parent / "src"))
from zapret_zen import __version__ as APP_VERSION

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringTable,
    StringStruct,
    VarFileInfo,
    VarStruct,
)

_m = re.search(r"^(\d+(?:\.\d+)*)", APP_VERSION)
_version_parts = tuple(int(x) for x in (_m.group(1) if _m else "0").split(".")[:4])
while len(_version_parts) < 4:
    _version_parts = _version_parts + (0,)

project_root = Path(SPECPATH).resolve().parent
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_version_parts,
        prodvers=_version_parts,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "peshk0v"),
                        StringStruct("FileDescription", "Zapret-Zen"),
                        StringStruct("FileVersion", APP_VERSION),
                        StringStruct("InternalName", "zapret_zen"),
                        StringStruct("OriginalFilename", "zapret_zen.exe"),
                        StringStruct("ProductName", "Zapret-Zen"),
                        StringStruct("ProductVersion", APP_VERSION),
                        StringStruct("Publisher", "peshk0v"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)
datas = [
    (str(project_root / "sample_data"), "sample_data"),
    (str(project_root / "runtime"), "runtime"),
    (str(project_root / "ui_assets"), "ui_assets"),
    (str(project_root / "themes"), "themes"),
    (str(project_root / "src" / "zapret_zen" / "scripts"), "scripts"),
    (str(project_root / "src" / "zapret_zen" / "translations"), "zapret_zen/translations"),
]
crypto_hiddenimports = collect_submodules("cryptography")
certifi_datas = collect_data_files("certifi")

a = Analysis(
    [str(project_root / "src" / "zapret_zen" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas + certifi_datas,
    hiddenimports=[
        "asyncio",
        "asyncio.base_events",
        "asyncio.base_futures",
        "asyncio.base_subprocess",
        "asyncio.events",
        "asyncio.futures",
        "asyncio.locks",
        "asyncio.protocols",
        "asyncio.queues",
        "asyncio.runners",
        "asyncio.selector_events",
        "asyncio.streams",
        "asyncio.subprocess",
        "asyncio.tasks",
        "asyncio.transports",
        "argparse",
        "base64",
        "collections",
        "dataclasses",
        "hashlib",
        "hmac",
        "logging",
        "logging.handlers",
        "os",
        "random",
        "socket",
        "ssl",
        "string",
        "struct",
        "threading",
        "typing",
        "urllib",
        "urllib.request",
    ] + crypto_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="zapret_zen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project_root / "ui_assets" / "icons" / "app.ico"),
    version=version_info,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="zapret_zen",
)
