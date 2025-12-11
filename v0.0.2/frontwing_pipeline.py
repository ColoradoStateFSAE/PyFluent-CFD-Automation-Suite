# frontwing_pipeline.py
# Front Wing CFD pipeline (class-based)

import os
from pipelines import BasePipeline


class FrontWingPipeline(BasePipeline):
    """
    CFD pipeline for isolated front wing validation.
    Inherits all Fluent handling behaviors from BasePipeline.
    """

    # =============================================================
    # 1. GEOMETRY SETUP
    # =============================================================
    def setup_geometry(self):
        self.log_info("Importing geometry for Front Wing...")

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
    # 2. SURFACE MESHING
    # =============================================================
    def mesh_surface(self):
        self.log_info("Generating Front Wing surface mesh...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        # Generate Surface Mesh
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
    # 3. VOLUME MESHING
    # =============================================================
    def mesh_volume(self):
        self.log_info("Generating Front Wing volume mesh...")

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
    # 4. SOLVER (3-STAGE RAMP)
    # =============================================================
    def run_solver_stages(self):
        tui = self.tui

        self.log_info("Loading mesh into solver...")
        tui.file.read_case(os.path.join(self.output_dir, "mesh.msh.h5"))

        # Enable GEKO turbulence model
        self.log_info("Configuring turbulence model (GEKO)...")
        tui.define.models.viscous.gko("yes")

        # -------------------------------
        # Stage 1 – coarse steady solve
        # -------------------------------
        self.log_info("Solver Ramp 1: 1000 iterations...")
        tui.solve.iterate(1000)
        self.progress(3)

        # -------------------------------
        # Stage 2 – enable curvature correction
        # -------------------------------
        self.log_info("Solver Ramp 2: enabling curvature correction...")
        tui.define.models.viscous.correction_factor("on")

        tui.solve.iterate(1000)
        self.progress(4)

        # -------------------------------
        # Stage 3 – long stable solve
        # -------------------------------
        self.log_info("Solver Ramp 3: 5000 iterations...")
        tui.solve.iterate(5000)
        self.progress(5)

        self.log_info("Solver completed for Front Wing.")

    # =============================================================
    # 5. EXPORT RESULTS
    # =============================================================
    def export_results(self):
        self.log_info("Exporting Front Wing results...")

        case_file = os.path.join(self.output_dir, f"{self.sim_name}.cas.h5")
        data_file = os.path.join(self.output_dir, f"{self.sim_name}.dat.h5")
        coeff_file = os.path.join(self.output_dir, f"{self.sim_name}_coeffs.txt")

        tui = self.tui

        # Save case & data
        tui.file.write_case_data(case_file)

        # Extract force coefficients
        with open(coeff_file, "w") as f:
            f.write("Front Wing Coefficients\n")
            f.write("------------------------\n")
            f.write(str(self.session.solution.force_monitor.get_force_coefficients()))

        self.log_info("Result files saved.")

