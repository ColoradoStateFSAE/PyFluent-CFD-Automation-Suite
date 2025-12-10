# rearwing_pipeline.py
# Ram Racing FSAE Aero Automation Suite
# Isolated Rear Wing CFD Pipeline

import os
import matplotlib.pyplot as plt
import ansys.fluent.core as pyfluent
from report_gen import generate_report


# ------------------------------------------------------------
# Small wait helper
# ------------------------------------------------------------
def wait():
    import time
    time.sleep(0.25)


# ------------------------------------------------------------
# Projected Area
# ------------------------------------------------------------
def compute_projected_area(solver, outdir):

    area_path = os.path.join(outdir, "projected_area.txt")

    try:
        solver.tui.report.surface_integrals.area("rearwing", "yes")
        out = solver.solver.get_fluent_stdout()

        area_val = None
        for line in out.splitlines()[::-1]:
            if "Surface area" in line or "surface area" in line:
                area_val = float(line.split()[-1])
                break

        if area_val is None:
            area_val = 0.0

        with open(area_path, "w") as f:
            f.write(str(area_val))

        return area_val

    except:
        with open(area_path, "w") as f:
            f.write("0.0")
        return 0.0


# ------------------------------------------------------------
# Contours
# ------------------------------------------------------------
def save_contours(solver, outdir):

    p_path = os.path.join(outdir, "pressure.png")
    v_path = os.path.join(outdir, "velocity.png")

    try:
        solver.tui.display.set.window(1)
        solver.tui.display.contours("pressure", "yes", "rearwing")
        solver.tui.display.save_picture(p_path)

        solver.tui.display.contours("velocity-magnitude", "yes", "rearwing")
        solver.tui.display.save_picture(v_path)

    except:
        pass

    return p_path, v_path


# ------------------------------------------------------------
# Residual Plot
# ------------------------------------------------------------
def save_residual_plot(solver, outdir):

    r_path = os.path.join(outdir, "residuals.png")

    try:
        res = solver.solution.monitor.get_data()
        its = res["iterations"]
        cont = res["continuity"]

        plt.figure(figsize=(6, 4))
        plt.semilogy(its, cont)
        plt.xlabel("Iterations")
        plt.ylabel("Residual")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(r_path)
        plt.close()

    except:
        pass

    return r_path


# ------------------------------------------------------------
# Coeff Extraction
# ------------------------------------------------------------
def extract_coeffs(solver, area):

    Cd = solver.tui.report.force_coefficients.drag("rearwing")
    Cl = solver.tui.report.force_coefficients.lift("rearwing")

    SCx = Cd * area
    SCz = Cl * area

    return Cd, Cl, SCx, SCz


# ------------------------------------------------------------
# Meshing
# ------------------------------------------------------------
def run_meshing(geom_path, outdir, L, W, H):

    session = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.MESHING,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=20,
        dimension=3,
        mpi_type="intel"
    )

    wf = session.workflow
    tasks = wf.TaskObject

    # Import geometry
    imp = tasks["Import Geometry"]
    imp.Arguments.set_state({"FileName": geom_path, "LengthUnit": "m"})
    imp.Execute()
    wait()

    # Curvature sizing
    add_ls = tasks["Add Local Sizing"]
    add_ls.AddChildToTask()
    ls = tasks["curvature_rw"]
    ls.Arguments.set_state({
        "LocalSizingType": "Curvature",
        "SizeControlType": "Curvature",
        "MinSize": 0.0005,
        "MaxSize": 0.008,
        "CurvatureNormalAngle": 9,
        "BoundaryNameList": ["rearwing"]
    })
    ls.Execute()
    wait()

    # Surface mesh
    surf = tasks["Generate the Surface Mesh"]
    surf.Arguments.set_state({
        "MinimumSize": 0.002,
        "MaximumSize": 0.256,
        "GrowthRate": 1.19999,
        "CurvatureNormalAngle": 18,
        "CellsPerGap": 1,
        "SizeFunctions": "CurvatureProximity"
    })
    surf.Execute()
    wait()

    # Improve surface mesh
    imps = tasks["Improve Surface Mesh"]
    imps.Arguments.set_state({"FaceQualityLimit": 0.7})
    imps.Execute()
    wait()

    # Describe geometry
    desc = tasks["Describe Geometry"]
    desc.Arguments.set_state({"SetupType": "The geometry consists of only fluid regions with no voids"})
    desc.Execute()
    wait()

    tasks["Update Boundaries"].Execute()
    wait()
    tasks["Update Regions"].Execute()
    wait()

    # Boundary layers
    bl = tasks["Add Boundary Layers"]
    bl.AddChildToTask()
    bl_task = tasks["last-ratio_1"]
    bl_task.Arguments.set_state({
        "BoundaryZones": ["rearwing"],
        "FirstLayerHeight": 0.0005,
        "NumberOfLayers": 10,
        "LastLayerRatio": 1.2
    })
    bl_task.Execute()
    wait()

    # Volume mesh
    vol = tasks["Generate the Volume Mesh"]
    vol.Arguments.set_state({
        "FillWith": "poly-hexcore",
        "MinCellLength": 0.0005,
        "MaxCellLength": 0.256,
        "PeelLayers": 1,
        "EnableParallel": True
    })
    vol.Execute()
    wait()

    # Improve volume mesh
    imv = tasks["Improve Volume Mesh"]
    imv.Arguments.set_state({"QualityMethod": "Orthogonal", "CellQualityLimit": 0.2})
    imv.Execute()
    wait()

    mesh_path = os.path.join(outdir, "rearwing_mesh.msh.h5")
    session.meshing.SaveMesh(file_name=mesh_path)

    return mesh_path


# ------------------------------------------------------------
# Solver
# ------------------------------------------------------------
def run_solver(mesh_path, outdir):

    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=20,
        dimension=3,
        mpi_type="intel"
    )

    # Load mesh
    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)
    wait()

    # Units
    solver.tui.define.units("velocity", "mph")
    solver.tui.define.units("force", "lbf")

    # GEKO
    solver.tui.define.models.viscous.ke_gko("yes")
    solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")

    # Inlet
    solver.tui.define.boundary_conditions.velocity_inlet("inlet", "yes",
        "velocity-magnitude", "40")

    # Ground
    solver.tui.define.boundary_conditions.wall("ground", "yes",
        "motion", "moving-wall",
        "moving-wall-speed", "40",
        "moving-wall-direction", "1", "0", "0")

    solver.tui.solve.reference_values.set("compute-from", "inlet")

    # Ramp
    solver.solution.RunCalculation.iterate(1000)
    solver.solution.RunCalculation.iterate(1000)

    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
    solver.solution.RunCalculation.iterate(5000)

    # Extract results
    area = compute_projected_area(solver, outdir)
    Cd, Cl, SCx, SCz = extract_coeffs(solver, area)

    p_img, v_img = save_contours(solver, outdir)
    r_img = save_residual_plot(solver, outdir)

    # Save case/data
    solver.solver.File.WriteCaseData(
        file_name=os.path.join(outdir, "final_rearwing")
    )

    return {
        "component": "Rear Wing",
        "geom": mesh_path,
        "mesh_file": mesh_path,
        "dimensions": {},
        "coeffs": {"Cd": Cd, "Cl": Cl, "SCx": SCx, "SCz": SCz},
        "contours": {
            "pressure": p_img,
            "velocity": v_img,
            "residuals": r_img
        }
    }


# ------------------------------------------------------------
# Export → PDF
# ------------------------------------------------------------
def export_results(results, outdir):
    return generate_report(results, outdir)
