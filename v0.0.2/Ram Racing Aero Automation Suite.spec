# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all

# ---------------------------------------------------------
# Get absolute path of this .spec file correctly
# PyInstaller does NOT set __file__, so we use cwd
# ---------------------------------------------------------
project_dir = os.getcwd()

# ---------------------------------------------------------
# Collect Pyside6 assets (Qt DLLs, plugins, etc.)
# ---------------------------------------------------------
pyside6_binaries, pyside6_datas, pyside6_hidden = collect_all("PySide6")

# ---------------------------------------------------------
# Bundle ansys.units YAML files
# ---------------------------------------------------------
import ansys.units
units_path = ansys.units.__path__[0]

datas = [
    (units_path, "ansys/units"),
] + pyside6_datas

# ---------------------------------------------------------
# Full hidden imports needed for Fluent + PySide6
# ---------------------------------------------------------
hiddenimports = [
    # ansys units
    "ansys.units",
    "ansys.units.quantity",
    "ansys.units.systems",
    "ansys.units._constants",
    "ansys.units.common",

    # Fluent Core
    "ansys.fluent.core",
    "ansys.fluent.core.session_solver_lite",
    "ansys.fluent.core.utils.dump_session_data",
    "ansys.fluent.core.utils.event_loop",
    "ansys.fluent.core.utils.test_grpc_connection",

    # Visualization
    "ansys.fluent.visualization",
    "ansys.fluent.visualization.contour",
    "ansys.fluent.visualization.matplotlib",
    "ansys.fluent.visualization.pyvista",
] + pyside6_hidden


block_cipher = None

a = Analysis(
    ['main_gui.py'],
    pathex=[project_dir],
    binaries=pyside6_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "PyQt5",   # Avoid conflicting Qt bindings
        "PyQt6",
        "qtpy"
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Ram Racing Aero Automation Suite",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
