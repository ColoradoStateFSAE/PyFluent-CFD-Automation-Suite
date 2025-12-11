# undertray_pipeline.py
# Undertray CFD pipeline for half-car underbody testing (class-based)

import os
from pipelines import BasePipeline


class UndertrayPipeline(BasePipeline):
    """
    CFD pipeline for the undertray alone (isolated geometry version).
    Includes diffuser geometry, wheel refinement, rotating wheels,
    and moving ground plane.
    """

    # =============================================================
    # 1. GEOMETRY IMPORT
    # =============================================================
    def setup_geometry(self):
        self.log_info("Importing geometry for Undertray...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        workflow.InitializeWorkflow(WorkflowType="Watertight Geometry")

        import_geom = tasks["Import Geometry"]
        import_geom.Arguments.set_state({
            "FileName": self.geom_path,
            "LengthUnit": "m"
        })
        import_geom.Execute()

        self.log_info("Geometry imported successfully.")

    # =============================================================
    # 2. SURFACE MESH GENERATION
    # =============================================================
    def mesh_surface(self):
        self.log_info("Generating Undertray surface mesh...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        surface_mesh = tasks["Generate the Surface Mesh"]

        #
        # Undertray typically requires aggressive curvature control
        # near diffuser strakes and sharp cutouts.
        #
        surface_mesh.Arguments.set_state({
            "CFDSurfaceMeshControls": {
                "CurvatureNormalAngle": 9,     # tighter for aero
                "MinSize": 0.0005,
                "MaxSize": 0.008,
                "GrowthRate": 1.2
            }
        })
        surface_mesh.Execute()

        self.log_info("Surface mesh complete.")

    # =============================================================
    # 3. VOLUME MESH GENERATION
    # =============================================================
    def mesh_volume(self):
        self.log_info("Generating Undertray volume mesh...")

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
    # 4. SOLVER SETUP & RAMP SEQUENCE
    # =============================================================
    def run_solver_stages(self):

        tui = self.tui
        out_case = os.path.join(self.output_dir, "mesh.msh.h5")

        self.log_info("Loading Undertray mesh into solver...")
        tui.file.read_case(out_case)

        # -------------------------------
        # Flow conditions
        # -------------------------------
        inlet_speed = 40 * 0.44704  # mph → m/s

        self.log_info("Applying boundary conditions...")

        tui.define.boundary_conditions.velocity_inlet(
            "inlet",
            "yes",
            f"{inlet_speed}"
        )

        # Wheels rotate at 88 rad/s
        wheel_rpm = 88

        rotating_wheels = ["fw", "rw"]
        for w in rotating_wheels:
            try:
                tui.define.boundary_conditions.wall(
                    w,
                    "moving-wall",
                    "yes",
                    "rotation-rate",
                    f"{wheel_rpm}",
                    "z",
                    "0"
                )
            except:
                self.log_info(f"Warning: wheel zone '{w}' not found (OK for isolated UT).")

        # Wheel blocks stay stationary
        wheel_blocks = ["fwb", "rwb"]
        for wb in wheel_blocks:
            try:
                tui.define.boundary_conditions.wall(wb, "stationary-wall", "no")
            except:
                pass

        # Moving ground
        self.log_info("Setting moving ground boundary...")
        tui.define.boundary_conditions.wall(
            "ground",
            "moving-wall",
            "yes",
            "speed",
            f"{inlet_speed}"
        )

        # Enable GEKO
        self.log_info("Configuring GEKO turbulence model...")
        tui.define.models.viscous.gko("yes")

        # =====================================================
        # Solver Ramp Sequence
        # =====================================================

        # -------------------------------
        # Stage 1 – 1000 iterations
        # -------------------------------
        self.log_info("Solver Ramp 1: 1000 iterations...")
        tui.solve.iterate(1000)
        self.progress(3)

        # -------------------------------
        # Stage 2 – curvature correction ON
        # -------------------------------
        self.log_info("Solver Ramp 2: enabling curvature correction...")
        tui.define.models.viscous.correction_factor("on")
        tui.solve.iterate(1000)
        self.progress(4)

        # -------------------------------
        # Stage 3 – long stabilization run
        # -------------------------------
        self.log_info("Solver Ramp 3: 5000 iterations...")
        tui.solve.iterate(5000)
        self.progress(5)

        self.log_info("Solver completed for Undertray.")

    # =============================================================
    # 5. EXPORT RESULTS
    # =============================================================
    def export_results(self):
        self.log_info("Exporting Undertray results...")

        tui = self.tui

        case_file = os.path.join(self.output_dir, f"{self.sim_name}.cas.h5")
        coeff_file = os.path.join(self.output_dir, f"{self.sim_name}_coeffs.txt")

        # Save case/data
        tui.file.write_case_data(case_file)

        # Extract aerodynamic coefficients
        coeffs = self.session.solution.force_monitor.get_force_coefficients()

        with open(coeff_file, "w") as f:
            f.write("Undertray Aerodynamic Coefficients\n")
            f.write("----------------------------------\n")
            f.write(str(coeffs))

        self.log_info("Undertray result files saved.")
