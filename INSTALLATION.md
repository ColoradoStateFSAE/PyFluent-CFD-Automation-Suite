# Installation Guide
This document explains how to install and configure the Ram Racing FSAE Aero Automation Suite for reliable operation on Windows and Linux using Ansys Fluent 2025R2.

## Requirements
- Python 3.12
- Ansys Fluent 2025R2 installed locally
- Valid Fluent license
- Correct Fluent environment variables
- Required Python packages:
  ```
  pip install pyqt5 reportlab matplotlib ansys-fluent-core
  ```

## Setting Up Fluent Environment (Windows)
Locate Fluent installation:
```
C:\Program Files\ANSYS Inc\v251\fluent
```

Set system variables:
- AWP_ROOT = C:\Program Files\ANSYS Inc\v251
- ANSYS_FLUENT_DIR = C:\Program Files\ANSYS Inc\v251\fluent

Add to PATH:
```
C:\Program Files\ANSYS Inc\v251\fluent\bin
C:\Program Files\ANSYS Inc\v251\CommonFiles\Tcl\bin
C:\Program Files\ANSYS Inc\v251\Framework\bin\Win64
C:\Program Files\ANSYS Inc\v251\commonfiles\MPI\Intel\2021.7\bin
```

Test Fluent:
```
fluent 3ddp -v
```

## Linux Setup
Add to ~/.bashrc:
```
export AWP_ROOT="/usr/ansys_inc/v251"
export ANSYS_FLUENT_DIR="/usr/ansys_inc/v251/fluent"
export PATH="$ANSYS_FLUENT_DIR/bin:$PATH"
export LD_LIBRARY_PATH="/usr/ansys_inc/v251/fluent/lib:$LD_LIBRARY_PATH"
```

Reload:
```
source ~/.bashrc
```

Test:
```
fluent 3ddp -g
```

## Running the GUI
```
python main_gui.py
```

## Building the EXE (Windows)
Use PowerShell:
```
pyinstaller --onefile --noconsole `
    --hidden-import=matplotlib `
    --hidden-import=reportlab `
    --hidden-import=ansys.fluent.core `
    --hidden-import=pipelines `
    --hidden-import=simulation_manager `
    --hidden-import=frontwing_pipeline `
    --hidden-import=rearwing_pipeline `
    --hidden-import=undertray_pipeline `
    --hidden-import=halfcar_pipeline `
    --name="Ram Racing Aero Automation Suite" `
    main_gui.py
```

## Deployment Notes
- The EXE requires Fluent environment variables.
- Fluent must be installed on the target machine.
