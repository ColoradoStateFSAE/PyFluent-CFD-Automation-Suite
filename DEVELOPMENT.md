# Developer Documentation

## Project Structure
```
main_gui.py
simulation_manager.py
pipelines.py
frontwing_pipeline.py
rearwing_pipeline.py
undertray_pipeline.py
halfcar_pipeline.py
report_gen.py
docs/
```

## Adding New Pipelines
1. Create new pipeline class.
2. Add to pipelines.py map.
3. Add button in GUI (optional).
4. Add logic in SimulationManager.

## Code Standards
- Use clear, deterministic arguments for Fluent
- Maintain deterministic meshing sequences
- Use try/except around Fluent TUI calls

## Building EXE
Use PyInstaller command from INSTALLATION.md.

