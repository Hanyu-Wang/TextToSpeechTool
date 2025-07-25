# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['gui.py'],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=[
        ('./static/audio', 'static/audio'),
        ('./ffmpeg', 'ffmpeg'),  # ✅ 打包整个 ffmpeg 文件夹
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TextToSpeechTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  #调试阶段可设为 True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
