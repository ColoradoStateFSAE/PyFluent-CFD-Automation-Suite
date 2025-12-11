# halfcar_pipeline.py
# Half-Car CFD pipeline (class-based)

import os
from pipelines import BasePipeline


class HalfCarPipeline(BasePipeline):
    """
    CFD pipeline for half-car aerodynamics.
    Includes inlet/outlet, moving ground, symmetry,
    rotating wheels, and full aero surfaces.
    """

    # =============================================================
    # 1. GEOMETRY IMPORT
    # =============================================================
    def setup_geometry(self):
        self.log_info("Importing half-car geometry...")

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
        self.log_info("Generating half-car surface mesh...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        surf = tasks["Generate the Surface Mesh"]
        surf.Arguments.set_state({
            "CFDSurfaceMeshControls": {
                "CurvatureNormalAngle": 12,
                "MinSize": 0.0005,
                "MaxSize": 0.032,
                "GrowthRate": 1.2
            }
        })
        surf.Execute()

        self.log_info("Surface mesh complete.")

    # =============================================================
    # 3. VOLUME MESH
    # =============================================================
    def mesh_volume(self):
        self.log_info("Generating half-car volume mesh...")

        workflow = self.session.workflow
        tasks = workflow.TaskObject

        vol = tasks["Generate the Volume Mesh"]
        vol.Arguments.set_state({
            "Solver": "Fluent",
            "FillWith": "poly-hexcore",
            "MinCellLength": 0.0005,
            "MaxCellLength": 0.256,
            "EnableParallel": True
        })
        vol.Execute()

        self.log_info("Volume mesh complete.")

    # =============================================================
    # 4. SOLVER SETUP (FULL HALF-CAR)
    # =============================================================
    def run_solver_stages(self):
        tui = self.tui
        mesh_file = os.path.join(self.output_dir, "mesh.msh.h5")

        self.log_info("Loading mesh into solver...")
        tui.file.read_case(mesh_file)

        inlet_speed = 40 * 0.44704  # mph → m/s

        # -------------------------------
        # Boundary Conditions
        # -------------------------------
        self.log_info("Applying boundary conditions...")

        # Inlet
        tui.define.boundary_conditions.velocity_inlet(
            "inlet", "yes", f"{inlet_speed}"
        )

        # Outlet
        tui.define.boundary_conditions.pressure_outlet("outlet", "yes")

        # Moving ground plane
        tui.define.boundary_conditions.wall(
            "ground", "moving-wall", "yes", "speed", f"{inlet_speed}"
        )

        # Symmetry
        tui.define.boundary_conditions.symmetry("symmetry")

        # Rotating wheels (88 rad/s)
        rotating = ["fw", "rw"]
        for w in rotating:
            try:
                tui.define.boundary_conditions.wall(
                    w, "moving-wall", "yes",
                    "rotation-rate", "88", "z", "0"
                )
            except:
                pass

        # Wheel blocks remain stationary
        blocks = ["fwb", "rwb"]
        for b in blocks:
            try:
                tui.define.boundary_conditions.wall(b, "stationary-wall", "no")
            except:
                pass

        # Turbulence model: GEKO
        tui.define.models.viscous.gko("yes")

        # =====================================================
        # SOLVER RAMP STAGES
        # =====================================================

        # Stage 1
        self.log_info("Solver Ramp 1: 1000 iterations...")
        tui.solve.iterate(1000)
        self.progress(3)

        # Stage 2 – curvature correction
        self.log_info("Solver Ramp 2: enabling curvature correction...")
        tui.define.models.viscous.correction_factor("on")
        tui.solve.iterate(1000)
        self.progress(4)

        # Stage 3 – long solve
        self.log_info("Solver Ramp 3: 5000 iterations...")
        tui.solve.iterate(5000)
        self.progress(5)

        self.log_info("Solver complete for Half-Car.")

    # =============================================================
    # 5. EXPORT RESULTS (Cd, Cl, SCx, SCz)
    # =============================================================
    def export_results(self):
        self.log_info("Exporting half-car results...")

        tui = self.tui

        case_file = os.path.join(self.output_dir, f"{self.sim_name}.cas.h5")
        coeff_file = os.path.join(self.output_dir, f"{self.sim_name}_coeffs.txt")

        # Save case/data
        tui.file.write_case_data(case_file)

        # Extract aerodynamic coefficients
        coeffs = self.session.solution.force_monitor.get_force_coefficients()

        # Projected frontal area (SCx, SCz reference)
        try:
            area = self.session.solution.surface_area.get_projected_area(
                surfaces=["frontwing", "rearwing", "undertray", "chassis",
                          "fw", "fwb", "rw", "rwb"],
                direction=[1, 0, 0],
                min_feature_size=0.0001
            )
        except:
            area = 0.0

        with open(coeff_file, "w") as f:
            f.write("Half-Car Aerodynamic Coefficients\n")
            f.write("--------------------------------\n\n")
            f.write(f"Coefficients: {coeffs}\n")
            f.write(f"Projected Area (SCx): {area}\n")

        self.log_info("Half-car results exported.")
