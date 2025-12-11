# base_pipeline.py
# Unified pipeline foundation for Fluent CFD automation using PyFluent

import os
import traceback
import ansys.fluent.core as pyfluent


class BasePipeline:
    """
    Base class for all CFD pipelines.
    Handles logging, progress, Fluent sessions, and common operations.
    """

    def __init__(self, geom_path, output_dir, sim_name,
                 L, W, H, logfn, progressfn):
        self.geom_path = geom_path
        self.output_dir = output_dir
        self.sim_name = sim_name

        self.L = L
        self.W = W
        self.H = H

        # Injected from SimulationManager
        self.log = logfn
        self.progress = progressfn

        self.session = None   # Fluent meshing or solver session
        self.tui = None       # Convenience alias

    # ------------------------------------------------------------
    # SAFE LOGGING
    # ------------------------------------------------------------
    def log_info(self, msg):
        """Thread-safe GUI logging."""
        self.log(f"[{self.sim_name}] {msg}")

    # ------------------------------------------------------------
    # SESSION LAUNCHING
    # ------------------------------------------------------------
    def launch_fluent_meshing(self):
        self.log_info("Launching Fluent Meshing...")
        try:
            self.session = pyfluent.launch_fluent(
                mode=pyfluent.FluentMode.MESHING,
                precision=pyfluent.Precision.DOUBLE,
                processor_count=12,
                dimension=3
            )
            self.tui = self.session.tui
            return True
        except Exception as e:
            self.log_info(f"ERROR launching fluent meshing: {e}")
            return False

    def launch_fluent_solver(self):
        self.log_info("Launching Fluent Solver...")
        try:
            self.session = pyfluent.launch_fluent(
                mode=pyfluent.FluentMode.SOLVER,
                precision=pyfluent.Precision.DOUBLE,
                processor_count=12,
                dimension=3
            )
            self.tui = self.session.tui
            return True
        except Exception as e:
            self.log_info(f"ERROR launching fluent solver: {e}")
            return False

    # ------------------------------------------------------------
    # ABSTRACT PLACEHOLDERS (implemented in children)
    # ------------------------------------------------------------
    def setup_geometry(self):
        raise NotImplementedError

    def mesh_surface(self):
        raise NotImplementedError

    def mesh_volume(self):
        raise NotImplementedError

    def run_solver_stages(self):
        raise NotImplementedError

    def export_results(self):
        raise NotImplementedError

    # ------------------------------------------------------------
    # MASTER EXECUTION PIPELINE
    # ------------------------------------------------------------
    def run(self):
        """Master execution order shared by all pipelines."""
        self.log_info("Starting CFD pipeline...")
        self.progress(0)

        # === 1. Meshing Phase ===
        if not self.launch_fluent_meshing():
            raise RuntimeError("Failed to start Fluent Meshing.")

        self.setup_geometry()

        # Surface mesh complete → stage 1
        self.mesh_surface()
        self.progress(1)

        # Volume mesh complete → stage 2
        self.mesh_volume()
        self.progress(2)

        # === 2. Solver Phase ===
        if not self.launch_fluent_solver():
            raise RuntimeError("Failed to start Fluent Solver.")

        # Ramp stages 1–3 → progress 3, 4, 5
        self.run_solver_stages()

        # === 3. Reporting Phase ===
        self.export_results()
        self.progress(6)

        self.log_info("Pipeline complete.")
        return {"status": "success", "sim": self.sim_name}
