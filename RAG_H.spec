# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\pc\\Desktop\\resources\\xy\\rag-qa-system\\config.json', '.'), ('C:\\Users\\pc\\Desktop\\resources\\xy\\rag-qa-system\\config.default.json', '.'), ('C:\\Users\\pc\\Desktop\\resources\\xy\\rag-qa-system\\assets', 'assets')]
binaries = []
hiddenimports = ['app.core', 'app.providers', 'app.ui', 'app.ui.workers', 'app.ui.widgets', 'app.utils']
tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\pc\\Desktop\\resources\\xy\\rag-qa-system\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='RAG_H',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\pc\\Desktop\\resources\\xy\\rag-qa-system\\assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RAG_H',
)
