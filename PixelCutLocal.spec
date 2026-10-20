# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PixelCut Local Windows executable distribution."""

import os
import sys
from pathlib import Path

block_cipher = None

# Base directories
project_root = Path(SPECPATH).resolve()
src_dir = project_root / "src"

# Static web UI assets
static_source = src_dir / "pixelcut_local" / "server" / "static"
datas = [
    (str(static_source), "pixelcut_local/server/static"),
]

# Hidden imports required by dynamic reflection
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespans",
    "uvicorn.lifespans.on",
    "fastapi",
    "fastapi.staticfiles",
    "starlette",
    "starlette.staticfiles",
    "python_multipart",
    "pydantic",
    "onnxruntime",
    "rembg",
    "scipy",
    "scipy.ndimage",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFilter",
    "PIL.ImageOps",
    "PIL.ImageEnhance",
    "qrcode",
    "qrcode.image.pil",
]

a = Analysis(
    [str(src_dir / "pixelcut_local" / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows onedir build (default and recommended)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PixelCutLocal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Set to True for console diagnostic builds
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PixelCutLocal",
)
