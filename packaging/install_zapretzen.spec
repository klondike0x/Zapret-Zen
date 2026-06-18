# -*- mode: python ; coding: utf-8 -*-

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH).resolve().parent / "src"))
from zapret_zen import __version__ as APP_VERSION

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
                        StringStruct("FileDescription", "Zapret-Zen Installer"),
                        StringStruct("FileVersion", APP_VERSION),
                        StringStruct("InternalName", "install_zapretzen"),
                        StringStruct("OriginalFilename", "install_zapretzen.exe"),
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
    (str(project_root / "installer_payload"), "installer_payload"),
    (str(project_root / "ui_assets"), "ui_assets"),
]

a = Analysis(
    [str(project_root / "installer" / "install_zapretzen.py")],
    pathex=[str(project_root), str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    name="install_zapretzen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    exclude_binaries=False,
    icon=str(project_root / "ui_assets" / "icons" / "app.ico"),
    version=version_info,
)
