# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Project directory: v0.0.2 (where main_gui.py and this spec live)
project_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

# ---------------------------
# Ansys / PyFluent data files
# ---------------------------
fluent_datas = collect_data_files("ansys.fluent.core", include_py_files=True)
units_datas = collect_data_files("ansys.units", include_py_files=True)

# Instance-management package + its metadata (needed at runtime)
inst_mgmt_datas = collect_data_files("ansys.platform.instancemanagement", include_py_files=True)
inst_mgmt_meta = collect_data_files("ansys-platform-instancemanagement", include_py_files=True)

datas = fluent_datas + units_datas + inst_mgmt_datas + inst_mgmt_meta

# Import “everything it might ever need”
hiddenimports = (
    collect_submodules("ansys.fluent.core") +
    collect_submodules("ansys.units") +
    collect_submodules("ansys.platform.instancemanagement")
)

a = Analysis(
    ['main_gui.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2'],  # keep only PySide6
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Ram Racing Aero Automation Suite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # change to True if you want a console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # drop an .ico here if you want
)
