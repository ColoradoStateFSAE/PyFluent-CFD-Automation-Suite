<img width="207" height="233" alt="RR2425_LogoGreen" src="https://github.com/user-attachments/assets/0967733d-0662-43cc-ac3a-1226af33b587" />

# Ram Racing FSAE Aero Automation Suite
Professional CFD Automation Framework for Ansys Fluent 2025R2  
Developed for high-performance aerodynamic evaluation and rapid iteration in Formula SAE applications.

---

## Overview
The **Ram Racing FSAE Aero Automation Suite** is a fully automated, GUI-based system designed to accelerate aerodynamic simulation workflows in **Ansys Fluent 2025R2**.  
It provides end-to-end automation for:

- Geometry import
- Meshing (Watertight Geometry Workflow)
- Boundary layer generation
- Automatic wheel refinement regions
- Poly-Hexcore volume mesh creation
- Solver setup with GEKO turbulence modeling
- Curvature Correction ramp activation
- Multi-stage solver convergence ramp
- Automatic coefficient extraction (Cd, Cl, SCx, SCz)
- Projected frontal area computation
- Residual, pressure, and velocity post-processing
- PDF report generation
- Queue-based batch simulation execution

The system includes four dedicated CFD pipelines:
- **Front Wing**
- **Rear Wing**
- **Undertray**
- **Half-Car Configuration**

All pipelines share a unified architecture for reliability, consistency, and maintainability.

---

## Key Features
### Aerodynamic Simulation Automation
- Complete pipeline from geometry to final report
- Zero manual Fluent interaction required
- GEKO turbulence modeling with automated Curvature Correction activation
- Wheel rotation and ground-moving wall setup (half-car pipeline)
- Region-specific local curvature sizing
- Tighter undertray meshing controls
- Automatic detection of enclosure regions
- Wheel refinement based on user-supplied chassis dimensions (L, W, H)

### Mesh Generation
- Watertight Geometry workflow
- Automated boundary layer controls (10 layers, configurable)
- Curvature-driven local sizing
- Auto-inserted refinement regions for wheel wakes
- Poly-Hexcore volume meshing
- Surface and volume mesh quality improvement passes

### Solver Automation
- Three ramp stages: 1000 / 1000 / 5000 iterations
- Automatic Curvature Correction activation after ramp stage 2
- Automatic reference value setup
- Convergence detection based on continuity
- Automatic solver restarts on floating-point errors (optional extension)

### Output Automation
Each simulation produces:
- Case/Data files (`.h5`)
- Pressure and velocity contour images
- Residual plots
- Coefficient CSV (Cd, Cl, SCx, SCz)
- Frontal area
- Mesh metrics (optional)
- Full PDF report

---

## Cross-Platform Support
The automation suite runs on **Windows** (recommended) and **Linux** systems.

- Windows: supports PyInstaller `.exe` packaging  
- Linux: supports standalone binary generation via PyInstaller  
- Fluent must be installed on the target system  
- Environment variables must be configured correctly (see `ENVIRONMENT.md`)

---

## License
This project is licensed under the **MIT License**.  
See `LICENSE` for details.

---

## Documentation
For full usage instructions, environment configuration guides, developer notes, and pipeline architecture, please refer to:

- `INSTALLATION.md`
- `USAGE.md`
- `PIPELINES.md`
- `ENVIRONMENT.md`
- `DEVELOPERS.md`
- `CHANGELOG.md`

---

## Contact
For questions, issues, or feature requests, please open a GitHub Issue or contact the project maintainer.

