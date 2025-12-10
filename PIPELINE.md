# Pipeline Architecture
This document describes the CFD pipelines used by the Ram Racing FSAE Aero Automation Suite.

## Common Structure
All pipelines implement:
- Geometry import
- Local curvature sizing
- Boundary layer generation
- Surface mesh generation and cleanup
- Volume mesh generation with poly-hexcore
- GEKO turbulence model
- Multi-stage solver ramp
- Automatic reporting

## Front Wing Pipeline
- No wheels
- Symmetry-supported
- Curvature sizing optimized for small aero surfaces
- Boundary layer: 10 layers, ratio=1.2

## Rear Wing Pipeline
Same as front wing with different zone targeting.

## Undertray Pipeline
Includes:
- Wheel refinement boxes
- Rotating wheels (88 rad/s)
- Stationary wheel blocks
- Tighter curvature sizing for diffuser and underbody

## Half-Car Pipeline
- Full vehicle minus right-hand side
- Boundary conditions:
  - Inlet: 40 mph
  - Ground: moving at 40 mph
  - Wheels: rotating
  - Symmetry on Z=0 plane
- Extracts Cd, Cl, SCx, SCz
- Computes projected area of aero surfaces

