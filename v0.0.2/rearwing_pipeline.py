# rearwing_pipeline.py
# Rear Wing CFD pipeline (class-based)

import os
from pipelines import BasePipeline


class RearWingPipeline(BasePipeline):
    """
    CFD pipeline for isolated rear wing validation.
    Inherits generic Fluent operations from BasePipeline.
    """

    # =============================================================
    # 1. GEOMETRY IMPORT
    # =============================================================
    def setup_geometry(self):
        self.log_info("Importing geometry for Rear Wing...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        workflow.InitializeWorkflow(WorkflowType="Watertight Geometry")

        import_geom = tasks["Import Geometry"]
        import_geom.Arguments.set_state({
            "FileName": self.geom_path,
            "LengthUnit": "m"
        })
        import_geom.Execute()

        self.log_info("Geometry imported.")

    # =============================================================
    # 2. SURFACE MESH
    # =============================================================
    def mesh_surface(self):
        self.log_info("Generating Rear Wing surface mesh...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        surface_mesh = tasks["Generate the Surface Mesh"]
        surface_mesh.Arguments.set_state({
            "CFDSurfaceMeshControls": {
                "CurvatureNormalAngle": 12,
                "MinSize": 0.001,
                "MaxSize": 0.032,
                "GrowthRate": 1.2
            }
        })
        surface_mesh.Execute()

        self.log_info("Surface mesh complete.")

    # =============================================================
    # 3. VOLUME MESH
    # =============================================================
    def mesh_volume(self):
        self.log_info("Generating Rear Wing volume mesh...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        volume_mesh = tasks["Generate the Volume Mesh"]
        volume_mesh.Arguments.set_state({
            "Solver": "Fluent",
            "FillWith": "poly-hexcore",
            "MinCellLength": 0.0005,
            "MaxCellLength": 0.256,
            "EnableParallel": True
        })
        volume_mesh.Execute()

        self.log_info("Volume mesh complete.")

    # =============================================================
    # 4. SOLVER — 3 RAMP STAGES
    # =============================================================
    def run_solver_stages(self):
        tui = self.tui

        self.log_info("Loading Rear Wing mesh into solver...")
        tui.file.read_case(os.path.join(self.output_dir, "mesh.msh.h5"))

        # Enable GEKO
        self.log_info("Configuring turbulence model (GEKO)...")
        tui.define.models.viscous.gko("yes")

        # -------------------------------
        # Stage 1 – Coarse solve
        # -------------------------------
        self.log_info("Solver Ramp 1: 1000 iterations...")
        tui.solve.iterate(1000)
        self.progress(3)

        # -------------------------------
        # Stage 2 – curvature correction
        # -------------------------------
        self.log_info("Solver Ramp 2: enabling curvature correction...")
        tui.define.models.viscous.correction_factor("on")

        tui.solve.iterate(1000)
        self.progress(4)

        # -------------------------------
        # Stage 3 – final long ramp
        # -------------------------------
        self.log_info("Solver Ramp 3: 5000 iterations...")
        tui.solve.iterate(5000)
        self.progress(5)

        self.log_info("Solver finished for Rear Wing.")

    # =============================================================
    # 5. EXPORT RESULTS
    # =============================================================
    def export_results(self):
        self.log_info("Exporting Rear Wing results...")

        tui = self.tui

        case_file = os.path.join(self.output_dir, f"{self.sim_name}.cas.h5")
        coeff_file = os.path.join(self.output_dir, f"{self.sim_name}_coeffs.txt")

        # Save case+data
        tui.file.write_case_data(case_file)

        # Extract aerodynamic coefficients
        coeffs = self.session.solution.force_monitor.get_force_coefficients()

        with open(coeff_file, "w") as f:
            f.write("Rear Wing Aerodynamic Coefficients\n")
            f.write("----------------------------------\n")
            f.write(str(coeffs))

        self.log_info("Rear Wing result files saved.")
