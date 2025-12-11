# -*- mode: python ; coding: utf-8 -*-

import os

# Your project root folder
project_dir = r"C:\Users\Hayes Dodson\PycharmProjects\FluentAuto\v0.0.2"

# All your pipeline scripts located next to main_gui.py
pipelines = [
    "frontwing_pipeline.py",
    "rearwing_pipeline.py",
    "undertray_pipeline.py",
    "halfcar_pipeline.py",
    "pipelines.py",
    "diagnostics.py",
    "simulation_manager.py",
    "report_gen.py",
    "worker_thread.py",
]

datas = []

# Include all pipeline files as data so PyInstaller ALWAYS bundles them
for f in pipelines:
    datas.append((os.path.join(project_dir, f), "."))

# Fix for Ansys metadata (ansys-platform-instancemanagement)
# We do NOT bundle the Fluent runtime — Fluent must already be installed
hiddenimports = [
    "ansys.fluent.core",
    "ansys.fluent.core.session",
    "ansys.fluent.core.solver",
    "ansys.fluent.core.utils",
    "ansys.fluent.core.launcher",
    "ansys.platform.instancemanagement",
    "importlib.metadata",
]

# Your main GUI entry file
main_script = os.path.join(project_dir, "main_gui.py")

block_cipher = None

a = Analysis(
    [main_script],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "qtpy",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Ram Racing Aero Automation Suite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(project_dir, "icon.ico") if os.path.exists(os.path.join(project_dir, "icon.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Ram Racing Aero Automation Suite",
)
