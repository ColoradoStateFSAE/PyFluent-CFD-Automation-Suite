# -*- mode: python ; coding: utf-8 -*-

import os
import ansys.units

cfg_yaml = os.path.join(ansys.units.__path__[0], "cfg.yaml")

block_cipher = None

a = Analysis(
    ['main_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # PyFluent required YAML file
        (cfg_yaml, 'ansys/units'),

        # Pipeline files (your project does NOT have a pipelines folder)
        ('frontwing_pipeline.py', '.'),
        ('rearwing_pipeline.py', '.'),
        ('undertray_pipeline.py', '.'),
        ('halfcar_pipeline.py', '.'),

        ('diagnostics.py', '.'),
        ('simulation_manager.py', '.'),
        ('worker_thread.py', '.'),
        ('report_gen.py', '.'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'ansys.fluent.core',
    ],
    excludes=[
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DRender',
        'PySide6.QtCharts',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtQuick',
        'PySide6.QtQml',
        'PySide6.QtSql',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Ram Racing Aero Automation Suite',
    console=False,
)
