# undertray_pipeline.py
# Ram Racing FSAE Aero Automation Suite
# Full undertray + wheels + bargeboard CFD pipeline

import os
import matplotlib.pyplot as plt
import ansys.fluent.core as pyfluent
from report_gen import generate_report


# ======================================================================
# Small wait helper
# ======================================================================
def wait():
    import time
    time.sleep(0.25)


# ======================================================================
# Wheel center definitions (fixed; DO NOT MOVE)
# ======================================================================
WHEEL_CENTERS = {
    "fw":  (-0.7874, 0.2032,  0.6096),   # Front Left (only left side model)
    "fwb": (-0.7874, 0.2032,  0.6096),   # Wheel block same center
    "rw":  ( 0.7874, 0.2032,  0.5842),   # Rear Left
    "rwb": ( 0.7874, 0.2032,  0.5842),
}

WHEEL_ROT_SPEED = 88.0  # rad/s


# ======================================================================
# Projected Area
# ======================================================================
def compute_projected_area(solver, outdir):
    area_path = os.path.join(outdir, "projected_area.txt")

    ZONES = ["undertray", "fw", "rw", "fwb", "rwb", "bargeboard"]

    total = 0.0

    try:
        for z in ZONES:
            solver.tui.report.surface_integrals.area(z, "yes")
            out = solver.solver.get_fluent_stdout()

            for line in out.splitlines()[::-1]:
                if "Surface area" in line:
                    val = float(line.split()[-1])
                    total += val
                    break

        with open(area_path, "w") as f:
            f.write(str(total))

        return total

    except:
        with open(area_path, "w") as f:
            f.write("0.0")
        return 0.0


# ======================================================================
# Contours
# ======================================================================
def save_contours(solver, outdir):

    p_path = os.path.join(outdir, "pressure.png")
    v_path = os.path.join(outdir, "velocity.png")

    try:
        solver.tui.display.set.window(1)
        solver.tui.display.contours("pressure", "yes", "undertray")
        solver.tui.display.save_picture(p_path)

        solver.tui.display.contours("velocity-magnitude", "yes", "undertray")
        solver.tui.display.save_picture(v_path)

    except:
        pass

    return p_path, v_path


# ======================================================================
# Residual Plot
# ======================================================================
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


# ======================================================================
# Coefficient Extraction
# ======================================================================
def extract_coeffs(solver, area):

    ZONES = ["undertray", "fw", "rw", "fwb", "rwb", "bargeboard"]

    Cd_total = 0.0
    Cl_total = 0.0

    for z in ZONES:
        Cd_total += solver.tui.report.force_coefficients.drag(z)
        Cl_total += solver.tui.report.force_coefficients.lift(z)

    SCx = Cd_total * area
    SCz = Cl_total * area

    return Cd_total, Cl_total, SCx, SCz


# ======================================================================
# Meshing
# ======================================================================
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

    # ------------------------------------------------------------
    # Import geometry
    # ------------------------------------------------------------
    imp = tasks["Import Geometry"]
    imp.Arguments.set_state({"FileName": geom_path, "LengthUnit": "m"})
    imp.Execute()
    wait()

    # ------------------------------------------------------------
    # Local sizing for Undertray & Bargeboard
    # ------------------------------------------------------------
    add_ls = tasks["Add Local Sizing"]
    add_ls.AddChildToTask()
    ls = tasks["curvature_ut"]
    ls.Arguments.set_state({
        "LocalSizingType": "Curvature",
        "SizeControlType": "Curvature",
        "MinSize": 0.0005,
        "MaxSize": 0.008,
        "CurvatureNormalAngle": 9,
        "BoundaryNameList": ["undertray", "bargeboard"]
    })
    ls.Execute()
    wait()

    # ------------------------------------------------------------
    # Wheel refinement regions (from your PDF)
    # ------------------------------------------------------------
    REFINEMENT_SF = tasks["Add Local Sizing"]
    # For each wheel & wheel block:
    #   refinement box = ±(L/20, H/10, W/10)

    for zone, pos in WHEEL_CENTERS.items():
        x, y, z = pos
        REFINEMENT_SF.AddChildToTask()
        child = tasks[f"refine_{zone}"]

        child.Arguments.set_state({
            "LocalSizingType": "BodyOfInfluence",
            "BOIType": "Box",
            "CenterCoordinates": [x, y, z],
            "XSize": L / 20,
            "YSize": H / 10,
            "ZSize": W / 10,
            "MinSize": 0.0007,
            "MaxSize": 0.032,
            "BoundaryNameList": [zone]
        })
        child.Execute()
        wait()

    # ------------------------------------------------------------
    # Surface mesh
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # Improve surface
    # ------------------------------------------------------------
    ims = tasks["Improve Surface Mesh"]
    ims.Arguments.set_state({"FaceQualityLimit": 0.7})
    ims.Execute()
    wait()

    # ------------------------------------------------------------
    # Describe Geo
    # ------------------------------------------------------------
    desc = tasks["Describe Geometry"]
    desc.Arguments.set_state({"SetupType": "The geometry consists of only fluid regions with no voids"})
    desc.Execute()
    wait()

    tasks["Update Boundaries"].Execute()
    wait()
    tasks["Update Regions"].Execute()
    wait()

    # ------------------------------------------------------------
    # Boundary layers
    # ------------------------------------------------------------
    bl = tasks["Add Boundary Layers"]
    bl.AddChildToTask()
    blc = tasks["last-ratio_1"]

    blc.Arguments.set_state({
        "BoundaryZones": ["undertray", "fw", "rw", "fwb", "rwb", "bargeboard"],
        "FirstLayerHeight": 0.0005,
        "NumberOfLayers": 10,
        "LastLayerRatio": 1.2
    })
    blc.Execute()
    wait()

    # ------------------------------------------------------------
    # Volume mesh
    # ------------------------------------------------------------
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

    # Save mesh
    mesh_path = os.path.join(outdir, "undertray_mesh.msh.h5")
    session.meshing.SaveMesh(file_name=mesh_path)

    return mesh_path


# ======================================================================
# Solver
# ======================================================================
def run_solver(mesh_path, outdir):

    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=20,
        dimension=3,
        mpi_type="intel"
    )

    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)
    wait()

    # Units
    solver.tui.define.units("velocity", "mph")
    solver.tui.define.units("force", "lbf")

    # GEKO model
    solver.tui.define.models.viscous.ke_gko("yes")
    solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")

    # Inlet 40 mph
    solver.tui.define.boundary_conditions.velocity_inlet("inlet", "yes",
        "velocity-magnitude", "40")

    # Ground moving at 40 mph
    solver.tui.define.boundary_conditions.wall("ground", "yes",
        "motion", "moving-wall",
        "moving-wall-speed", "40",
        "moving-wall-direction", "1", "0", "0")

    # Wheels rotate but wheel BLOCKS do not
    for zone in ["fw", "rw", "fwb", "rwb"]:
        solver.tui.define.boundary_conditions.wall(zone, "yes",
            "motion", "rotational",
            "origin", *WHEEL_CENTERS[zone],
            "rotation-axis-components", "0", "1", "0",
            "rotation-rate", str(WHEEL_ROT_SPEED))

    solver.tui.solve.reference_values.set("compute-from", "inlet")

    # ------------------------------------------------------------
    # Ramp
    # ------------------------------------------------------------
    solver.solution.RunCalculation.iterate(1000)
    solver.solution.RunCalculation.iterate(1000)

    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
    solver.solution.RunCalculation.iterate(5000)

    # ------------------------------------------------------------
    # Extract results
    # ------------------------------------------------------------
    area = compute_projected_area(solver, outdir)
    Cd, Cl, SCx, SCz = extract_coeffs(solver, area)

    p_img, v_img = save_contours(solver, outdir)
    r_img = save_residual_plot(solver, outdir)

    solver.solver.File.WriteCaseData(
        file_name=os.path.join(outdir, "final_undertray")
    )

    return {
        "component": "Undertray",
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


# ======================================================================
# Export results → PDF
# ======================================================================
def export_results(results, outdir):
    return generate_report(results, outdir)
