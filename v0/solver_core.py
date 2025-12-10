# solver_core.py
import os
import ansys.fluent.core as pyfluent

def run_component_solver(mesh_path, outdir, zones, sim_name):
    # Launch solver
    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=16,
        dimension=3,
        mpi_type="intel",
    )

    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)

    # Units
    solver.tui.define.units("force", "lbf")
    solver.tui.define.units("velocity", "mph")

    # Turbulence model (GEKO, no curvature correction)
    solver.tui.define.models.viscous.ke_gko("yes")
    solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")

    # Boundary conditions
    solver.tui.define.boundary_conditions.velocity_inlet(
        "inlet", "yes", "velocity-magnitude", "40"
    )

    solver.tui.define.boundary_conditions.wall(
        "ground", "yes",
        "motion", "moving-wall",
        "moving-wall-speed", "40",
        "moving-wall-direction", "1", "0", "0"
    )

    wheels = ["fw", "rw", "fwb", "rwb"]
    for w in wheels:
        solver.tui.define.boundary_conditions.wall(
            w, "yes",
            "motion", "rotational",
            "rotation-rate", "88",
            "rotation-axis-origin", "0", "0", "0",
            "rotation-axis-direction", "0", "1", "0"
        )

    # Reference values
    solver.tui.solve.reference_values.set("velocity", "40")
    solver.tui.solve.reference_values.set("compute-from", "inlet")

    # Ramping
    solver.solution.RunCalculation.iterate(1000)
    solver.solution.RunCalculation.iterate(1000)

    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
    solver.solution.RunCalculation.iterate(5000)

    # Force extraction
    solver.tui.report.force_coefficients.setup(
        "force-coeff",
        "zone-names", *zones,
        "reference-area", "1.0",
        "reference-length", "1.0",
        "force-vector", "1", "0", "0",
        "moment-center", "0", "0", "0"
    )

    cd = solver.tui.report.force_coefficients.c_d()
    cl = solver.tui.report.force_coefficients.c_l()

    with open(os.path.join(outdir, f"{sim_name}_forces.txt"), "w") as f:
        f.write(f"Cd = {cd}\nCl = {cl}")

    print("\n--------------------------------")
    print(f"Force Coefficients for {sim_name}")
    print("--------------------------------")
    print(f"Cd = {cd}")
    print(f"Cl = {cl}")
