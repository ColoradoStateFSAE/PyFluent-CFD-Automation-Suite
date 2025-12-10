##############################################
# FSAE UNDERTRAY CFD AUTOMATION SCRIPT
# Full Meshing + Solver Pipeline
# Fluent 2025R2 — Watertight Geometry Workflow
# Includes Wheels, Wheel Blocks, Bargeboards
# Wheels rotate at 88 rad/s — Wheel blocks do NOT move
##############################################

import os
import time
import math
import ansys.fluent.core as pyfluent


###########################################################
# ---- GLOBAL CONSTANTS ----
###########################################################

# Wheel angular velocity (rad/s)
WHEEL_OMEGA = 88.0


###########################################################
# ---- USER INPUT HANDLING ----
###########################################################

def ask_user_inputs():
    print("\n===========================================")
    print("      FSAE CFD AUTOMATION — UNDERTRAY")
    print("===========================================\n")

    geom = input("Enter full path to UNDERTRAY geometry (.step or .stp): ").strip()
    while not os.path.isfile(geom):
        geom = input("❗ File not found. Enter geometry file path again: ").strip()

    sim_name = input("Enter simulation name (e.g., UT_test01): ").strip()
    if sim_name == "":
        sim_name = "undertray_sim"

    print("\nENTER VEHICLE BOUNDING BOX DIMENSIONS (M)")
    L = float(input("Vehicle Length  L (m): ").strip())
    W = float(input("Vehicle Width   W (m): ").strip())
    H = float(input("Vehicle Height  H (m): ").strip())

    outdir = os.path.join(os.getcwd(), sim_name)
    os.makedirs(outdir, exist_ok=True)

    return geom, sim_name, outdir, L, W, H


###########################################################
# ---- PRINT + WAIT UTILITIES ----
###########################################################

def print_header(msg):
    print("\n" + "=" * 70)
    print(msg)
    print("=" * 70 + "\n")

def wait():
    time.sleep(0.25)


###########################################################
# ---- WHEEL COORDINATES (HALF CAR LEFT SIDE) ----
###########################################################

def get_wheel_centers():
    """
    Returns the confirmed FL + RL wheel centers for half-car simulation.
    Wheel blocks DO NOT move.
    """

    FL = (-0.7874, 0.2032, 0.6096)
    RL = ( 0.7874, 0.2032, 0.5842)

    return {"fw": FL, "rw": RL}


###########################################################
# ---- WHEEL ROTATION BC SETUP ----
###########################################################

def apply_wheel_rotation(solver, wheel_name, center):
    """
    Applies rotational moving-wall boundary condition to a wheel.
    Wheel blocks are NOT rotated.
    """

    x, y, z = center

    try:
        solver.tui.define.boundary_conditions.wall(
            wheel_name, "yes",
            "motion", "rotational",
            "rotational-speed", f"{WHEEL_OMEGA}",
            "rotation-origin-x", f"{x}",
            "rotation-origin-y", f"{y}",
            "rotation-origin-z", f"{z}",
            "rotation-axis-x", "0",
            "rotation-axis-y", "1",
            "rotation-axis-z", "0"
        )
        print(f"[BC] Wheel {wheel_name} rotating at {WHEEL_OMEGA} rad/s")
    except:
        print(f"[BC] ERROR applying rotation to wheel: {wheel_name}")


###########################################################
# ---- RESIDUAL MONITORING ----
###########################################################

def get_continuity_residual(solver):
    """Retrieve continuity residual."""
    try:
        res = solver.solution.Monitors.Residual.GetValues()
        return res.get("continuity", None)
    except:
        return None


def wait_until_converged(solver, target=1e-4, max_wait=2400):
    """
    Poll continuity until below threshold (target = 1e-4).
    max_wait = seconds allowed (default 40 minutes)
    """

    print("\n[Monitor] Watching continuity until < {:.1e}".format(target))
    start = time.time()

    while True:
        res = get_continuity_residual(solver)
        if res is not None:
            print(f"   continuity = {res:.3e}")
            if res < target:
                print("[Monitor] Converged.\n")
                return True

        if time.time() - start > max_wait:
            print("[Monitor] Timeout waiting for convergence.\n")
            return False

        time.sleep(2)


###########################################################
# ---- CASE + DATA SAVING ----
###########################################################

def save_case_data(solver, outdir):
    try:
        case_file = os.path.join(outdir, "final.cas.h5")
        data_file = os.path.join(outdir, "final.dat.h5")

        solver.solver.File.Write(file_type="case", file_name=case_file)
        solver.solver.File.Write(file_type="data", file_name=data_file)

        print(f"[Save] Case saved → {case_file}")
        print(f"[Save] Data saved → {data_file}\n")

    except Exception as e:
        print(f"[Save] ERROR saving case/data: {e}")


###########################################################
# ---- EXPORT CONTOURS ----
###########################################################

def export_contours(solver, outdir):
    press = os.path.join(outdir, "pressure.png")
    vel = os.path.join(outdir, "velocity.png")

    try:
        solver.tui.display.set_window(1)
        solver.tui.display.contour("pressure", "static-pressure", "yes")
        solver.tui.display.save_picture(press)
        print(f"[Post] Pressure contour saved → {press}")
    except:
        print("[Post] Pressure contour failed.")

    try:
        solver.tui.display.set_window(1)
        solver.tui.display.contour("velocity", "velocity-magnitude", "yes")
        solver.tui.display.save_picture(vel)
        print(f"[Post] Velocity contour saved → {vel}")
    except:
        print("[Post] Velocity contour failed.")


###########################################################
# ---- PROJECTED AREA CALCULATION ----
###########################################################

def compute_projected_area(solver, outdir):
    txt = os.path.join(outdir, "projected_area.txt")
    try:
        solver.tui.solve.reference_values.compute("projected-area")
        area = solver.tui.solve.reference_values.area()

        with open(txt, "w") as f:
            f.write(str(area))

        print(f"[Area] Projected frontal area = {area}\n")
        return float(area)
    except:
        print("[Area] ERROR computing projected area.")
        return None


###########################################################
# ---- AERO COEFFICIENT EXTRACTION ----
###########################################################

def extract_aero_coeffs(solver, outdir, area):
    """
    Reads Cd, Cl directly from Fluent.
    Computes SCx = Cd*A
    Computes SCz = Cl*A
    Writes everything to text file.
    """

    txt = os.path.join(outdir, "aero_coeffs.txt")

    try:
        cd = solver.tui.report.force_coefficients.c_d()
        cl = solver.tui.report.force_coefficients.c_l()

        scx = cd * area
        scz = cl * area

        with open(txt, "w") as f:
            f.write(f"Cd = {cd}\n")
            f.write(f"Cl = {cl}\n")
            f.write(f"SCx = {scx}\n")
            f.write(f"SCz = {scz}\n")

        print("\n[Aero Results — UNDERTRAY]")
        print(f"   Cd  = {cd}")
        print(f"   Cl  = {cl}")
        print(f"   SCx = {scx}")
        print(f"   SCz = {scz}\n")

        return cd, cl, scx, scz

    except Exception as e:
        print(f"[Aero] ERROR extracting aero coefficients: {e}")
        return None, None, None, None

###########################################################
# ---- MESHING PIPELINE (UNDERTRAY + WHEELS) ----
###########################################################

def run_meshing(session, geom_path, outdir, L, W, H):
    workflow = session.workflow
    tasks = workflow.TaskObject

    print_header("IMPORTING GEOMETRY")

    # ------------------------------------------------------
    # 1. IMPORT GEOMETRY
    # ------------------------------------------------------
    imp = tasks["Import Geometry"]
    imp.Arguments.set_state({
        "FileName": geom_path,
        "LengthUnit": "m"
    })
    imp.Execute()
    wait()


    ###########################################################
    # REFINEMENT REGIONS — NEAR / MID / FAR (GLOBAL)
    ###########################################################
    print_header("CREATING GLOBAL LOCAL REFINEMENT REGIONS")

    near_size = 0.016
    mid_size  = 0.032
    far_size  = 0.064

    zmin = 0
    zmax = W * 0.5  # symmetric half model

    box_defs = {
        "local-refinement-near": {
            "MeshSize": near_size,
            "Xmin": -L*0.65,
            "Xmax":  L*2.2,
            "Ymin":  0,
            "Ymax":  H*1.5,
            "Zmin":  zmin,
            "Zmax":  zmax
        },
        "local-refinement-mid": {
            "MeshSize": mid_size,
            "Xmin": -L*0.72,
            "Xmax":  L*4.1,
            "Ymin":  0,
            "Ymax":  H*2.2,
            "Zmin":  zmin,
            "Zmax":  zmax
        },
        "local-refinement-far": {
            "MeshSize": far_size,
            "Xmin": -L*0.78,
            "Xmax":  L*6.0,
            "Ymin":  0,
            "Ymax":  H*3.0,
            "Zmin":  zmin,
            "Zmax":  zmax
        },
    }

    add_refine = tasks["Create Local Refinement Regions"]

    for name, params in box_defs.items():
        add_refine.AddChildToTask()
        child = tasks[name]
        child.Arguments.set_state(params)
        child.Execute()
        wait()


    ###########################################################
    # WHEEL REFINEMENT REGIONS (CYLINDERS + FRONT/BACK BOXES)
    ###########################################################

    print_header("CREATING WHEEL REFINEMENT REGIONS")

    wheels = get_wheel_centers()

    wheel_refine = tasks["Create Local Refinement Regions"]

    for wname, (x, y, z) in wheels.items():

        # -------------------------
        # Wheel cylindrical region
        # -------------------------
        wheel_refine.AddChildToTask()
        cyl_task = tasks[f"wheel-cylinder-{wname}"]
        cyl_task.Arguments.set_state({
            "CoordinateSpecificationMethod": "Direct",
            "RegionType": "Cylinder",
            "CenterX": x,
            "CenterY": y,
            "CenterZ": z,
            "AxisX1": x,
            "AxisY1": y + 0.3,
            "AxisZ1": z,
            "Radius": 0.254,    # ~5 in radius
            "Height": 0.25,
            "MeshSize": 0.016
        })
        cyl_task.Execute()
        wait()

        # -------------------------
        # Front refinement box
        # -------------------------
        wheel_refine.AddChildToTask()
        front_box = tasks[f"wheel-front-{wname}"]
        front_box.Arguments.set_state({
            "CoordinateSpecificationMethod": "Direct",
            "MeshSize": 0.016,
            "Xmin": x - 0.25,
            "Xmax": x - 0.05,
            "Ymin": y - 0.3,
            "Ymax": y + 0.3,
            "Zmin": z - 0.2,
            "Zmax": z + 0.2
        })
        front_box.Execute()
        wait()

        # -------------------------
        # Wake refinement box (rear)
        # -------------------------
        wheel_refine.AddChildToTask()
        wake_box = tasks[f"wheel-wake-{wname}"]
        wake_box.Arguments.set_state({
            "CoordinateSpecificationMethod": "Direct",
            "MeshSize": 0.032,
            "Xmin": x + 0.05,
            "Xmax": x + 0.40,
            "Ymin": y - 0.3,
            "Ymax": y + 0.3,
            "Zmin": z - 0.2,
            "Zmax": z + 0.2
        })
        wake_box.Execute()
        wait()


    ###########################################################
    # CURVATURE SIZING (UNDERTRAY + WHEELS + BLOCKS + BARGEBOARD)
    ###########################################################

    print_header("APPLYING CURVATURE SIZING")

    curvature_sizing_targets = [
        ("curvature_undertray", ["undertray"], 0.0005, 0.008, 9),
        ("curvature_wheels", ["fw", "rw"], 0.0005, 0.032, 18),
        ("curvature_blocks", ["fwb", "rwb"], 0.0005, 0.032, 18),
        ("curvature_bargeboard", ["bargeboard"], 0.0005, 0.016, 12),
    ]

    sizing_task = tasks["Add Local Sizing"]

    for task_name, zones, min_s, max_s, angle in curvature_sizing_targets:
        sizing_task.AddChildToTask()
        child = tasks[task_name]
        child.Arguments.set_state({
            "LocalSizingType": "Curvature",
            "SizeControlType": "Curvature",
            "MinSize": min_s,
            "MaxSize": max_s,
            "CurvatureNormalAngle": angle,
            "BoundaryNameList": zones
        })
        child.Execute()
        wait()


    ###########################################################
    # SURFACE MESH GENERATION
    ###########################################################

    print_header("GENERATING SURFACE MESH")

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


    ###########################################################
    # SURFACE MESH IMPROVEMENT
    ###########################################################

    print_header("IMPROVING SURFACE MESH")

    improve_surf = tasks["Improve Surface Mesh"]
    improve_surf.Arguments.set_state({
        "FaceQualityLimit": 0.7
    })
    improve_surf.Execute()
    wait()


    ###########################################################
    # DESCRIBE GEOMETRY
    ###########################################################

    desc = tasks["Describe Geometry"]
    desc.Arguments.set_state({
        "SetupType": "The geometry consists of only fluid regions with no voids"
    })
    desc.Execute()
    wait()


    ###########################################################
    # UPDATE BOUNDARIES + REGIONS
    ###########################################################

    tasks["Update Boundaries"].Execute()
    wait()

    tasks["Update Regions"].Execute()
    wait()


    ###########################################################
    # BOUNDARY LAYERS — ALL RELEVANT ZONES
    ###########################################################

    print_header("ADDING BOUNDARY LAYERS")

    bl_zones = ["undertray", "fw", "rw", "fwb", "rwb", "bargeboard"]

    bl = tasks["Add Boundary Layers"]
    bl.AddChildToTask()
    bl_task = tasks["last-ratio_1"]

    bl_task.Arguments.set_state({
        "BoundaryZones": bl_zones,
        "FirstLayerHeight": 0.0005,
        "NumberOfLayers": 10,
        "LastLayerRatio": 1.2
    })
    bl_task.Execute()
    wait()


    ###########################################################
    # VOLUME MESH — POLY-HEXCORE
    ###########################################################

    print_header("GENERATING POLY-HEXCORE VOLUME MESH")

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


    ###########################################################
    # VOLUME MESH IMPROVEMENT
    ###########################################################

    print_header("IMPROVING VOLUME MESH")

    impv = tasks["Improve Volume Mesh"]
    impv.Arguments.set_state({
        "QualityMethod": "Orthogonal",
        "CellQualityLimit": 0.2
    })
    impv.Execute()
    wait()


    ###########################################################
    # SAVE FINAL MESH
    ###########################################################

    mesh_out = os.path.join(outdir, "mesh_undertray.msh.h5")
    try:
        session.meshing.SaveMesh(file_name=mesh_out)
        print(f"[Mesh] Final UNDERTRAY mesh saved → {mesh_out}")
    except Exception as e:
        print(f"[Mesh] ERROR saving mesh: {e}")

    return mesh_out

###########################################################
# ---- SOLVER PIPELINE (UNDERTRAY + WHEELS) ----
###########################################################

def run_solver(mesh_path, outdir):
    print_header("LAUNCHING FLUENT SOLVER (UNDERTRAY)")

    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=20,
        dimension=3,
        mpi_type="intel",
    )
    wait()

    # --------------------------------------------------------
    # LOAD MESH
    # --------------------------------------------------------
    print("[Solver] Loading mesh...")
    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)
    wait()


    ###########################################################
    # SET UNITS
    ###########################################################
    print_header("SETTING UNITS → lbf, mph")
    try:
        solver.tui.define.units("force", "lbf")
        solver.tui.define.units("velocity", "mph")
    except:
        print("[Units] ERROR setting units")


    ###########################################################
    # ENABLE GEKO TURBULENCE MODEL
    ###########################################################
    print_header("ENABLING GEKO TURBULENCE MODEL")

    try:
        solver.tui.define.models.viscous.ke_gko("yes")
        solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
        solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")
        print("[Turbulence] GEKO ON (curvature correction OFF)")
    except:
        print("[Turbulence] ERROR enabling GEKO")


    ###########################################################
    # APPLY BOUNDARY CONDITIONS
    ###########################################################
    print_header("APPLYING BOUNDARY CONDITIONS")

    # --------------------
    # Inlet
    # --------------------
    try:
        solver.tui.define.boundary_conditions.velocity_inlet(
            "inlet", "yes",
            "velocity-magnitude", "40"
        )
        print("[BC] inlet = 40 mph")
    except:
        print("[BC] ERROR setting inlet")


    # --------------------
    # Moving ground
    # --------------------
    try:
        solver.tui.define.boundary_conditions.wall(
            "ground", "yes",
            "motion", "moving-wall",
            "moving-wall-speed", "40",
            "moving-wall-direction", "1", "0", "0"
        )
        print("[BC] ground moving at 40 mph")
    except:
        print("[BC] ERROR setting ground motion")


    # --------------------
    # Wheels (rotate at 88 rad/s)
    # --------------------
    wheels = get_wheel_centers()

    for wname, center in wheels.items():
        apply_wheel_rotation(solver, wname, center)

    # --------------------
    # Wheel blocks → DO NOT MOVE
    # --------------------
    for block in ["fwb", "rwb"]:
        try:
            solver.tui.define.boundary_conditions.wall(
                block, "yes",
                "motion", "stationary"
            )
            print(f"[BC] Wheel block {block} = fixed wall")
        except:
            print(f"[BC] ERROR assigning wheel block BC: {block}")


    ###########################################################
    # REFERENCE VALUES
    ###########################################################
    print_header("SETTING REFERENCE VALUES")

    try:
        solver.tui.solve.reference_values.set("velocity", "40")
        solver.tui.solve.reference_values.set("compute-from", "inlet")
        print("[Reference] Computed from inlet @ 40 mph")
    except:
        print("[Reference] ERROR setting reference values")


    ###########################################################
    # PROJECTED AREA
    ###########################################################
    print_header("COMPUTING PROJECTED AREA")
    area = compute_projected_area(solver, outdir)


    ###########################################################
    # DISCRETIZATION & RELAXATION
    ###########################################################
    print_header("SETTING DISCRETIZATION & RELAXATION")

    try:
        solver.tui.solve.set.p_v_coupling("SIMPLE")

        solver.tui.solve.set.discretization_scheme("pressure", "PRESTO!")
        solver.tui.solve.set.discretization_scheme("momentum", "second-order-upwind")
        solver.tui.solve.set.discretization_scheme("turb-kinetic-energy", "second-order-upwind")
        solver.tui.solve.set.discretization_scheme("turb-diss-rate", "second-order-upwind")

        solver.tui.solve.set.relaxation_factors(
            "pressure", "0.2",
            "momentum", "0.3",
            "turb-kinetic-energy", "0.3",
            "turb-diss-rate", "0.3"
        )

    except:
        print("[Solver] ERROR setting discretization")


    ###########################################################
    # SOLVER RAMP-UP
    ###########################################################

    print_header("RAMP PHASE 1 → 1000 iterations")
    solver.solution.RunCalculation.iterate(1000)
    wait()

    print_header("RAMP PHASE 2 → 1000 iterations")
    solver.solution.RunCalculation.iterate(1000)
    wait()

    print_header("RAMP PHASE 3 → enable curvature correction + 5000 iterations")

    try:
        solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
        print("[GEKO] Curvature correction ON")
    except:
        print("[GEKO] ERROR enabling curvature correction")

    solver.solution.RunCalculation.iterate(5000)
    wait()


    ###########################################################
    # CHECK CONVERGENCE
    ###########################################################
    print_header("CHECKING CONTINUITY RESIDUAL")

    converged = wait_until_converged(
        solver,
        target=1e-4,
        max_wait=2400
    )


    ###########################################################
    # FORCE COEFFICIENTS (Cd, Cl, SCx, SCz)
    ###########################################################
    print_header("EXTRACTING UNDERTRAY AERO COEFFICIENTS")

    cd, cl, scx, scz = extract_aero_coeffs(
        solver=solver,
        outdir=outdir,
        area=area
    )


    ###########################################################
    # CONTOUR EXPORT
    ###########################################################
    print_header("EXPORTING CONTOURS")
    export_contours(solver, outdir)


    ###########################################################
    # SAVE CASE + DATA
    ###########################################################
    print_header("SAVING FINAL CASE & DATA")
    save_case_data(solver, outdir)

    print_header("SOLVER COMPLETE — UNDERTRAY FINISHED")

    return cd, cl, scx, scz

###########################################################
# ---- MAIN WORKFLOW (UNDERTRAY + WHEELS + BLOCKS) ----
###########################################################

def main():
    print_header("FSAE UNDERTRAY CFD — FULL AUTOMATION")

    # ------------------------------------------
    # USER INPUT
    # ------------------------------------------
    geom_path, sim_name, outdir, L, W, H = ask_user_inputs()

    # ------------------------------------------
    # START FLUENT MESHING
    # ------------------------------------------
    print_header("LAUNCHING FLUENT MESHING SESSION")

    meshing_session = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.MESHING,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=20,
        dimension=3,
        mpi_type="intel",
    )
    wait()

    # ------------------------------------------
    # RUN MESHING PIPELINE
    # ------------------------------------------
    print_header("RUNNING UNDERTRAY MESHING PIPELINE")

    mesh_file = run_meshing(
        session=meshing_session,
        geom_path=geom_path,
        outdir=outdir,
        L=L, W=W, H=H
    )

    print_header("MESHING COMPLETE — MOVING TO SOLVER")


    # ------------------------------------------
    # RUN SOLVER PIPELINE
    # ------------------------------------------
    cd, cl, scx, scz = run_solver(
        mesh_path=mesh_file,
        outdir=outdir
    )

    # ------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------
    print_header("UNDERTRAY CFD — SUMMARY")

    print(f"Simulation Name:   {sim_name}")
    print(f"Geometry Used:     {geom_path}")
    print(f"Output Folder:     {outdir}\n")

    print("AERODYNAMIC RESULTS (UNDERTRAY SYSTEM):")
    print(f"   Cd  = {cd}")
    print(f"   Cl  = {cl}")
    print(f"   SCx = {scx}")
    print(f"   SCz = {scz}\n")

    print("===============================================")
    print("     UNDERTRAY SIMULATION COMPLETE ✔")
    print("===============================================\n")


###########################################################
# ---- ENTRY POINT ----
###########################################################

if __name__ == "__main__":
    main()
