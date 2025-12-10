# Usage Guide
This document explains how to operate the Ram Racing FSAE Aero Automation Suite through the GUI.

## Starting the Application
Run:
```
python main_gui.py
```
or the packaged EXE:
```
Ram Racing Aero Automation Suite.exe
```

## GUI Components
### Input Fields
- Geometry Path
- Output Directory
- Simulation Name
- L (chassis length)
- W (chassis width)
- H (chassis height)

### Pipeline Buttons
- Run Front Wing
- Run Rear Wing
- Run Undertray
- Run Half Car

### Queue Controls
- Add to Queue Only
- Start Queue

### Log Window
Displays execution progress, Fluent launch status, solver iteration stages, and report generation.

### Queue List
Shows all pending simulations with assigned pipeline types.

## Running a Simulation
1. Select geometry file (.stp, .igs, .step).
2. Choose output folder.
3. Enter simulation name.
4. Enter L, W, H.
5. Click a pipeline button.
6. Start queue.

## Output Structure
Each simulation produces:
- Mesh file (.msh.h5)
- Case/Data files (.h5)
- Pressure/velocity contour images
- Residual plot
- Coefficient CSV
- Projected area file
- PDF report

