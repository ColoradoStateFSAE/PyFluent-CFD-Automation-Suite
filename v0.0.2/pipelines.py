# pipelines.py
# Ram Racing FSAE Aero Automation Suite
# Unified wrapper for all CFD pipelines (FW, RW, UT, HC)

import os
import traceback

# Import the four actual CFD pipeline implementations
from frontwing_pipeline import (
    run_meshing as fw_run_meshing,
    run_solver as fw_run_solver,
    export_results as fw_export_results
)

from rearwing_pipeline import (
    run_meshing as rw_run_meshing,
    run_solver as rw_run_solver,
    export_results as rw_export_results
)

from undertray_pipeline import (
    run_meshing as ut_run_meshing,
    run_solver as ut_run_solver,
    export_results as ut_export_results
)

from halfcar_pipeline import (
    run_meshing as hc_run_meshing,
    run_solver as hc_run_solver,
    export_results as hc_export_results
)



# ===============================================================
# BASE PIPELINE CLASS (ABSTRACT)
# ===============================================================

class BasePipeline:
    def __init__(self, geom_path, sim_dir, L, W, H):
        self.geom_path = geom_path
        self.sim_dir = sim_dir
        self.L = L
        self.W = W
        self.H = H

        # Ensure output folder exists
        os.makedirs(sim_dir, exist_ok=True)

    # ---- To be overridden by subclasses ----
    def run_meshing(self):
        raise NotImplementedError

    def run_solver(self, mesh_path):
        raise NotImplementedError

    def export_results(self, results):
        raise NotImplementedError

    # ---- Unified run() used by the simulation manager ----
    def run(self):
        """Full pipeline: mesh → solve → export."""
        try:
            mesh_path = self.run_meshing()
            sim_results = self.run_solver(mesh_path)
            report_path = self.export_results(sim_results)
            return report_path

        except Exception as e:
            print("PIPELINE ERROR:", e)
            print(traceback.format_exc())
            raise

# ===============================================================
# FRONT WING PIPELINE WRAPPER
# ===============================================================

class FrontWingPipeline(BasePipeline):
    def run_meshing(self):
        return fw_run_meshing(
            geom_path=self.geom_path,
            outdir=self.sim_dir,
            L=self.L, W=self.W, H=self.H
        )

    def run_solver(self, mesh_path):
        return fw_run_solver(
            mesh_path=mesh_path,
            outdir=self.sim_dir
        )

    def export_results(self, results):
        return fw_export_results(
            results=results,
            outdir=self.sim_dir
        )



# ===============================================================
# REAR WING PIPELINE WRAPPER
# ===============================================================

class RearWingPipeline(BasePipeline):
    def run_meshing(self):
        return rw_run_meshing(
            geom_path=self.geom_path,
            outdir=self.sim_dir,
            L=self.L, W=self.W, H=self.H
        )

    def run_solver(self, mesh_path):
        return rw_run_solver(
            mesh_path=mesh_path,
            outdir=self.sim_dir
        )

    def export_results(self, results):
        return rw_export_results(
            results=results,
            outdir=self.sim_dir
        )



# ===============================================================
# UNDERTRAY PIPELINE WRAPPER
# ===============================================================

class UndertrayPipeline(BasePipeline):
    def run_meshing(self):
        return ut_run_meshing(
            geom_path=self.geom_path,
            outdir=self.sim_dir,
            L=self.L, W=self.W, H=self.H
        )

    def run_solver(self, mesh_path):
        return ut_run_solver(
            mesh_path=mesh_path,
            outdir=self.sim_dir
        )

    def export_results(self, results):
        return ut_export_results(
            results=results,
            outdir=self.sim_dir
        )



# ===============================================================
# HALF CAR PIPELINE WRAPPER
# ===============================================================

class HalfCarPipeline(BasePipeline):
    def run_meshing(self):
        return hc_run_meshing(
            geom_path=self.geom_path,
            outdir=self.sim_dir,
            L=self.L, W=self.W, H=self.H
        )

    def run_solver(self, mesh_path):
        return hc_run_solver(
            mesh_path=mesh_path,
            outdir=self.sim_dir
        )

    def export_results(self, results):
        return hc_export_results(
            results=results,
            outdir=self.sim_dir
        )
