# halfcar_pipeline.py
# Ram Racing FSAE Aero Automation Suite
# Full Half-Car CFD Pipeline

import os
import matplotlib.pyplot as plt
import ansys.fluent.core as pyfluent
from report_gen import generate_report


# ======================================================================
# Helper wait
# ======================================================================
def wait():
    import time
    time.sleep(0.25)


# ======================================================================
# Wheel properties
# ======================================================================
WHEEL_CENTERS = {
    "fw":  (-0.7874, 0.2032,  0.6096),   # front wheel
    "fwb": (-0.7874, 0.2032,  0.6096),   # front block
    "rw":  ( 0.7874, 0.2032,  0.5842),   # rear wheel
    "rwb": ( 0.7874, 0.2032,  0.5842),   # rear block
}

WHEEL_ROT_SPEED = 88.0  # rad/s


# ======================================================================
# Aero zones used for SCx/SCz
# ======================================================================
AERO_ZONES = ["frontwing", "rearwing", "undertray"]


# ======================================================================
# Auto-detect enclosure zone
# ======================================================================
def detect_enclosure(face_zones):
    for z in face_zones:
        if "enclosure" in z.lower():
            return z
    return None


# ======================================================================
# Projected Area
# ======================================================================
def compute_projected_area(solver, outdir):

    AP = os.path.join(outdir, "projected_area.txt")
    total = 0.0

    try:
        for zone in AERO_ZONES:
            solver.tui.report.surface_integrals.area(zone, "yes")
            out = solver.solver.get_fluent_stdout()

            for line in out.splitlines()[::-1]:
                if "Surface area" in line:
                    total += float(line.split()[-1])
                    break

        with open(AP, "w") as f:
            f.write(str(total))

        return total

    except:
        with open(AP, "w") as f:
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
# Residuals
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
# Extract SCx, SCz, Cd, Cl
# ======================================================================
def extract_coeffs(solver, area):

    Cd = 0.0
    Cl = 0.0

    for zone in AERO_ZONES:
        Cd += solver.tui.report.force_coefficients.drag(zone)
        Cl += solver.tui.report.force_coefficients.lift(zone)

    SCx = Cd * area
    SCz = Cl * area

    return Cd, Cl, SCx, SCz


# ======================================================================
# Meshing Pipeline
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

    # -------------------------------------------------------------
    # Import Geometry
    # -------------------------------------------------------------
    imp = tasks["Import Geometry"]
    imp.Arguments.set_state({"FileName": geom_path, "LengthUnit": "m"})
    imp.Execute()
    wait()

    # -------------------------------------------------------------
    # Local Sizing — FRONT WING (standard)
    # -------------------------------------------------------------
    add_ls = tasks["Add Local Sizing"]
    add_ls.AddChildToTask()
    ls_fw = tasks["ls_fw"]
    ls_fw.Arguments.set_state({
        "LocalSizingType": "Curvature",
        "SizeControlType": "Curvature",
        "MinSize": 0.0005,
        "MaxSize": 0.008,
        "CurvatureNormalAngle": 9,
        "BoundaryNameList": ["frontwing"],
    })
    ls_fw.Execute()
    wait()

    # -------------------------------------------------------------
    # Local Sizing — REAR WING (standard)
    # -------------------------------------------------------------
    add_ls.AddChildToTask()
    ls_rw = tasks["ls_rw"]
    ls_rw.Arguments.set_state({
        "LocalSizingType": "Curvature",
        "SizeControlType": "Curvature",
        "MinSize": 0.0005,
        "MaxSize": 0.008,
        "CurvatureNormalAngle": 9,
        "BoundaryNameList": ["rearwing"],
    })
    ls_rw.Execute()
    wait()

    # -------------------------------------------------------------
    # Local Sizing — UNDERTRAY (tighter)
    # -------------------------------------------------------------
    add_ls.AddChildToTask()
    ls_ut = tasks["ls_ut"]
    ls_ut.Arguments.set_state({
        "LocalSizingType": "Curvature",
        "SizeControlType": "Curvature",
        "MinSize": 0.0003,
        "MaxSize": 0.006,
        "CurvatureNormalAngle": 9,
        "BoundaryNameList": ["undertray"],
    })
    ls_ut.Execute()
    wait()

    # -------------------------------------------------------------
    # Wheel Refinement BOI Regions
    # -------------------------------------------------------------
    add_ls = tasks["Add Local Sizing"]

    for zone, pos in WHEEL_CENTERS.items():
        x, y, z = pos
        add_ls.AddChildToTask()
        ref = tasks[f"refine_{zone}"]

        ref.Arguments.set_state({
            "LocalSizingType": "BodyOfInfluence",
            "BOIType": "Box",
            "CenterCoordinates": [x, y, z],
            "XSize": L / 20,
            "YSize": H / 10,
            "ZSize": W / 10,
            "MinSize": 0.0007,
            "MaxSize": 0.032,
            "BoundaryNameList": [zone],
        })
        ref.Execute()
        wait()

    # -------------------------------------------------------------
    # Surface Mesh
    # -------------------------------------------------------------
    surf = tasks["Generate the Surface Mesh"]
    surf.Arguments.set_state({
        "MinimumSize": 0.002,
        "MaximumSize": 0.256,
        "GrowthRate": 1.19999,
        "CurvatureNormalAngle": 18,
        "CellsPerGap": 1,
        "SizeFunctions": "CurvatureProximity",
    })
    surf.Execute()
    wait()

    # Improve Surface
    ims = tasks["Improve Surface Mesh"]
    ims.Arguments.set_state({"FaceQualityLimit": 0.7})
    ims.Execute()
    wait()

    # -------------------------------------------------------------
    # Describe Geometry
    # -------------------------------------------------------------
    desc = tasks["Describe Geometry"]
    desc.Arguments.set_state({"SetupType": "The geometry consists of only fluid regions with no voids"})
    desc.Execute()
    wait()

    tasks["Update Boundaries"].Execute()
    wait()
    tasks["Update Regions"].Execute()
    wait()

    # -------------------------------------------------------------
    # Boundary Layers
    # -------------------------------------------------------------
    bl = tasks["Add Boundary Layers"]
    bl.AddChildToTask()
    blc = tasks["last-ratio_1"]

    blc.Arguments.set_state({
        "BoundaryZones": ["frontwing", "rearwing", "undertray"],
        "FirstLayerHeight": 0.0005,
        "NumberOfLayers": 10,
        "LastLayerRatio": 1.2,
    })
    blc.Execute()
    wait()

    # -------------------------------------------------------------
    # Volume Mesh
    # -------------------------------------------------------------
    vol = tasks["Generate the Volume Mesh"]
    vol.Arguments.set_state({
        "FillWith": "poly-hexcore",
        "MinCellLength": 0.0005,
        "MaxCellLength": 0.256,
        "PeelLayers": 1,
        "EnableParallel": True,
    })
    vol.Execute()
    wait()

    # Improve Volume
    imv = tasks["Improve Volume Mesh"]
    imv.Arguments.set_state({"QualityMethod": "Orthogonal", "CellQualityLimit": 0.2})
    imv.Execute()
    wait()

    # Save Mesh
    mesh_path = os.path.join(outdir, "halfcar_mesh.msh.h5")
    session.meshing.SaveMesh(file_name=mesh_path)

    return mesh_path


# ======================================================================
# Solver Pipeline
# ======================================================================
def run_solver(mesh_path, outdir):

    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=20,
        dimension=3,
        mpi_type="intel",
    )

    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)
    wait()

    # Units
    solver.tui.define.units("velocity", "mph")
    solver.tui.define.units("force", "lbf")

    # GEKO
    solver.tui.define.models.viscous.ke_gko("yes")
    solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")

    # Boundary conditions
    solver.tui.define.boundary_conditions.velocity_inlet("inlet", "yes",
        "velocity-magnitude", "40")

    solver.tui.define.boundary_conditions.pressure_outlet("outlet", "yes")

    # Symmetry
    solver.tui.define.boundary_conditions.symmetry("symmetry", "yes")

    # Ground moving at 40 mph
    solver.tui.define.boundary_conditions.wall("ground", "yes",
        "motion", "moving-wall",
        "moving-wall-speed", "40",
        "moving-wall-direction", "1", "0", "0")

    # Wheel rotation
    for zone in ["fw", "rw"]:
        cx, cy, cz = WHEEL_CENTERS[zone]
        solver.tui.define.boundary_conditions.wall(zone, "yes",
            "motion", "rotational",
            "origin", cx, cy, cz,
            "rotation-axis-components", "0", "1", "0",
            "rotation-rate", str(WHEEL_ROT_SPEED))

    # Wheel blocks = stationary
    for zone in ["fwb", "rwb"]:
        solver.tui.define.boundary_conditions.wall(zone, "yes",
            "motion", "stationary")

    solver.tui.solve.reference_values.set("compute-from", "inlet")

    # -------------------------------------------------------------
    # Ramp
    # -------------------------------------------------------------
    solver.solution.RunCalculation.iterate(1000)
    solver.solution.RunCalculation.iterate(1000)
    solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
    solver.solution.RunCalculation.iterate(5000)

    # Extract values
    area = compute_projected_area(solver, outdir)
    Cd, Cl, SCx, SCz = extract_coeffs(solver, area)

    p_img, v_img = save_contours(solver, outdir)
    r_img = save_residual_plot(solver, outdir)

    solver.solver.File.WriteCaseData(
        file_name=os.path.join(outdir, "final_halfcar")
    )

    return {
        "component": "Half Car",
        "geom": mesh_path,
        "mesh_file": mesh_path,
        "dimensions": {},
        "coeffs": {"Cd": Cd, "Cl": Cl, "SCx": SCx, "SCz": SCz},
        "contours": {
            "pressure": p_img,
            "velocity": v_img,
            "residuals": r_img,
        },
    }


# ======================================================================
# Export to PDF
# ======================================================================
def export_results(results, outdir):
    return generate_report(results, outdir)
