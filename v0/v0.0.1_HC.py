##############################################
# FSAE CFD Automation Script (Single File)
# Fluent 2025R2 • Watertight Geometry Workflow
# Written for Hayes Dodson (CSU FSAE)
##############################################

import os
import time
import math
import ansys.fluent.core as pyfluent


###########################################################
# ---- USER INPUT INTERFACE ----
###########################################################

def ask_user_inputs():
    print("\n==============================")
    print("      FSAE CFD AUTOMATION")
    print("==============================\n")

    geom = input("Enter full path to geometry file (.step or .stp): ").strip()
    while not os.path.isfile(geom):
        geom = input("❗ File not found. Enter geometry file path again: ").strip()

    sim_name = input("Enter simulation name: ").strip()
    if sim_name == "":
        sim_name = "fsae_sim"

    # Build output directory
    outdir = os.path.join(os.getcwd(), sim_name)
    os.makedirs(outdir, exist_ok=True)

    return geom, sim_name, outdir


###########################################################
# ---- UTILITY FUNCTIONS ----
###########################################################

def print_header(msg):
    print("\n" + "=" * 65)
    print(msg)
    print("=" * 65 + "\n")


def wait():
    """Small delay to let Fluent catch up."""
    time.sleep(0.2)


###########################################################
# ---- RESIDUAL MONITORING ----
###########################################################

def get_continuity_residual(solver):
    """Returns continuity residual value."""
    try:
        res = solver.solution.Monitors.Residual.GetValues()
        return res.get("continuity", None)
    except:
        return None


def wait_until_converged(solver, target=1e-4, max_wait=300):
    """
    Poll continuity until below threshold.
    max_wait = seconds allowed
    """
    print("\n[Monitor] Waiting for continuity < {:.1e}".format(target))
    t0 = time.time()

    while True:
        res = get_continuity_residual(solver)
        if res is not None:
            print(f"   continuity = {res:.3e}")
            if res < target:
                print("\n[Monitor] Converged.")
                return True

        if time.time() - t0 > max_wait:
            print("\n[Monitor] WARNING — Timeout waiting for convergence.")
            return False

        time.sleep(2)


###########################################################
# ---- CASE/DATA SAVE HELPERS ----
###########################################################

def save_case_data(solver, outdir):
    try:
        case_path = os.path.join(outdir, "final.cas.h5")
        data_path = os.path.join(outdir, "final.dat.h5")
        solver.solver.File.Write(file_type="case", file_name=case_path)
        solver.solver.File.Write(file_type="data", file_name=data_path)
        print(f"[Save] Case saved to: {case_path}")
        print(f"[Save] Data saved to: {data_path}")
    except Exception as e:
        print(f"[Save] ERROR saving case/data: {e}")


###########################################################
# ---- CONTOUR EXPORT ----
###########################################################

def export_contours(solver, outdir):
    """Exports pressure + velocity contours."""
    press_png = os.path.join(outdir, "pressure.png")
    vel_png = os.path.join(outdir, "velocity.png")

    try:
        solver.tui.display.set_window(1)
        solver.tui.display.contour("pressure", "static-pressure", "yes")
        solver.tui.display.save_picture(press_png)
        print(f"[Post] Pressure contour saved → {press_png}")
    except:
        print("[Post] Pressure contour failed.")

    try:
        solver.tui.display.set_window(1)
        solver.tui.display.contour("velocity", "velocity-magnitude", "yes")
        solver.tui.display.save_picture(vel_png)
        print(f"[Post] Velocity contour saved → {vel_png}")
    except:
        print("[Post] Velocity contour failed.")


###########################################################
# ---- PROJECTED AREA (METHOD 1) ----
###########################################################

def compute_projected_area(solver, outdir):
    """
    Uses Fluent's Projected Area tool (Method 1)
    Along +X direction.
    """
    txt = os.path.join(outdir, "projected_area.txt")
    try:
        solver.tui.solve.reference_values.compute("projected-area")
        area = solver.tui.solve.reference_values.area()

        with open(txt, "w") as f:
            f.write(str(area))

        print(f"[Area] Projected frontal area = {area}")
        return float(area)

    except Exception as e:
        print(f"[Area] ERROR computing projected area: {e}")
        return None


###########################################################
# ---- AERO COEFFICIENT EXTRACTION ----
###########################################################

def extract_aero_coeffs(solver, outdir, area):
    """
    Reads Cd, Cl from Fluent's force report.
    Computes SCx and SCz.
    """
    txt = os.path.join(outdir, "aero_coeffs.txt")

    try:
        solver.tui.report.force_coefficients.print()

        cd = solver.tui.report.force_coefficients.c_d()
        cl = solver.tui.report.force_coefficients.c_l()

        scx = cd * area
        scz = cl * area

        with open(txt, "w") as f:
            f.write(f"Cd: {cd}\n")
            f.write(f"Cl: {cl}\n")
            f.write(f"SCx: {scx}\n")
            f.write(f"SCz: {scz}\n")

        print("\n[Aero]")
        print(f"   Cd  = {cd}")
        print(f"   Cl  = {cl}")
        print(f"   SCx = {scx}")
        print(f"   SCz = {scz}")

        return cd, cl, scx, scz

    except Exception as e:
        print(f"[Aero] ERROR extracting aero coefficients: {e}")
        return None, None, None, None

###########################################################
# ---- MESHING PIPELINE (WATERTIGHT GEOMETRY WORKFLOW) ----
###########################################################

def run_meshing(session, geom_path, outdir):
    workflow = session.workflow
    tasks = workflow.TaskObject

    print_header("IMPORTING GEOMETRY")

    # -------------------------------
    # 1. Import geometry
    # -------------------------------
    imp = tasks["Import Geometry"]
    imp.Arguments.set_state({
        "FileName": geom_path,
        "LengthUnit": "m"
    })
    imp.Execute()
    wait()


    ###############################################################
    # BUILD ALL REFINEMENT BOXES (FINE RESOLUTION)
    ###############################################################

    print_header("CREATING LOCAL REFINEMENT REGIONS")

    # Fine mesh sizes:
    near_size = 0.016
    mid_size  = 0.032
    far_size  = 0.064

    # Vehicle dimensions:
    L = 3.1
    W = 1.40462
    H = 1.19507039

    # Half car: Z from 0 → +W/2
    zmin = 0
    zmax = W * 0.5

    # Define refinement boxes per your PDF & requirements:
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

    # Create each refinement region
    add_refine = tasks["Create Local Refinement Regions"]

    for name, params in box_defs.items():
        add_refine.AddChildToTask()
        child = tasks[name]
        child.Arguments.set_state({
            "CoordinateSpecificationMethod": "Direct",
            "MeshSize": params["MeshSize"],
            "Xmin": params["Xmin"],
            "Xmax": params["Xmax"],
            "Ymin": params["Ymin"],
            "Ymax": params["Ymax"],
            "Zmin": params["Zmin"],
            "Zmax": params["Zmax"]
        })
        child.Execute()
        wait()


    ###############################################################
    # WHEEL REFINEMENT BOXES (FOLLOWS YOUR DOCUMENT)
    ###############################################################

    # Wheel centers – must match your earlier definitions
    FL = (-0.7874, 0.2032,  0.6096)
    FR = (-0.7874, 0.2032, -0.6096)
    RL = ( 0.7874, 0.2032,  0.5842)
    RR = ( 0.7874, 0.2032, -0.5842)

    wheel_centers = {
        "local-refinement-fw": [FL, FR],
        "local-refinement-rw": [RL, RR]
    }

    wheel_box_radius = 0.20  # 20 cm box radius around each wheel

    for name, centers in wheel_centers.items():
        add_refine.AddChildToTask()
        child = tasks[name]

        # Compute bounding box around wheels
        xs = [c[0] for c in centers]
        ys = [c[1] for c in centers]
        zs = [c[2] for c in centers]

        child.Arguments.set_state({
            "CoordinateSpecificationMethod": "Direct",
            "MeshSize": near_size,
            "Xmin": min(xs) - wheel_box_radius,
            "Xmax": max(xs) + wheel_box_radius,
            "Ymin": min(ys) - wheel_box_radius,
            "Ymax": max(ys) + wheel_box_radius,
            "Zmin": min(zs) - wheel_box_radius,
            "Zmax": max(zs) + wheel_box_radius,
        })
        child.Execute()
        wait()


    ###############################################################
    # CURVATURE SIZING (Stuff / Wheels / Aero)
    ###############################################################

    print_header("APPLYING CURVATURE-BASED LOCAL SIZING")

    add_sizing = tasks["Add Local Sizing"]

    curvature_groups = {
        "curvature_stuff": {
            "Min": 0.001,
            "Max": 0.064,
            "Angle": 12,
            "Labels": ["chassis"],
        },
        "curvature_wheels": {
            "Min": 0.0005,
            "Max": 0.032,
            "Angle": 18,
            "Labels": ["fw", "rw", "fwb", "rwb"],
        },
        "curvature_aero": {
            "Min": 0.0005,
            "Max": 0.008,
            "Angle": 9,
            "Labels": ["frontwing", "rearwing", "undertray"],
        },
    }

    for name, params in curvature_groups.items():
        add_sizing.AddChildToTask()
        child = tasks[name]
        child.Arguments.set_state({
            "LocalSizingType": "Curvature",
            "SizeControlType": "Curvature",
            "MinSize": params["Min"],
            "MaxSize": params["Max"],
            "CurvatureNormalAngle": params["Angle"],
            "BoundaryNameList": params["Labels"]
        })
        child.Execute()
        wait()


    ###############################################################
    # SURFACE MESH
    ###############################################################

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


    # Improve surface mesh
    print_header("IMPROVING SURFACE MESH")
    improve_surf = tasks["Improve Surface Mesh"]
    improve_surf.Arguments.set_state({
        "FaceQualityLimit": 0.7
    })
    improve_surf.Execute()
    wait()


    ###############################################################
    # DESCRIBE GEOMETRY
    ###############################################################

    desc = tasks["Describe Geometry"]
    desc.Arguments.set_state({
        "SetupType": "The geometry consists of only fluid regions with no voids"
    })
    desc.Execute()
    wait()


    ###############################################################
    # UPDATE BOUNDARIES / REGIONS
    ###############################################################

    tasks["Update Boundaries"].Execute()
    wait()

    tasks["Update Regions"].Execute()
    wait()


    ###############################################################
    # BOUNDARY LAYERS — 10 layers, growth 1.2
    ###############################################################

    print_header("ADDING BOUNDARY LAYERS")

    bl = tasks["Add Boundary Layers"]
    bl.AddChildToTask()
    child = tasks["last-ratio_1"]

    child.Arguments.set_state({
        "BoundaryZones": [
            "chassis", "frontwing", "rearwing", "undertray",
            "fw", "rw", "fwb", "rwb"
        ],
        "FirstLayerHeight": 0.0005,
        "NumberOfLayers": 10,
        "LastLayerRatio": 1.2
    })

    child.Execute()
    wait()


    ###############################################################
    # VOLUME MESHING — POLY-HEXCORE
    ###############################################################

    print_header("GENERATING VOLUME MESH")

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


    ###############################################################
    # IMPROVE VOLUME MESH
    ###############################################################

    print_header("IMPROVING VOLUME MESH")

    impv = tasks["Improve Volume Mesh"]
    impv.Arguments.set_state({
        "QualityMethod": "Orthogonal",
        "CellQualityLimit": 0.2
    })
    impv.Execute()
    wait()


    ###############################################################
    # SAVE FINAL MESH
    ###############################################################

    mesh_out = os.path.join(outdir, "mesh.msh.h5")
    try:
        session.meshing.SaveMesh(file_name=mesh_out)
        print(f"[Mesh] Final mesh saved → {mesh_out}")
    except Exception as e:
        print(f"[Mesh] ERROR saving mesh: {e}")

    return mesh_out

###########################################################
# ---- SOLVER PIPELINE ----
###########################################################

def run_solver(mesh_path, outdir):
    print_header("LAUNCHING FLUENT SOLVER")

    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=16,
        dimension=3,
        mpi_type="intel",
    )
    wait()

    print("[Solver] Reading mesh...")
    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)
    wait()

    ###############################################################
    # UNITS — LBF & MPH
    ###############################################################
    print_header("SETTING UNITS")
    try:
        solver.tui.define.units("force", "lbf")
        solver.tui.define.units("velocity", "mph")
        print("[Units] Force = lbf, Velocity = mph")
    except:
        print("[Units] Unit assignment failed (check available units).")

    ###############################################################
    # TURBULENCE MODEL — GEKO (NO CURVATURE CORRECTION YET)
    ###############################################################
    print_header("SETTING TURBULENCE MODEL")
    try:
        solver.tui.define.models.viscous.ke_gko("yes")
        solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
        solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")
        print("[Turbulence] GEKO enabled (no curvature correction).")
    except:
        print("[Turbulence] ERROR setting GEKO model.")

    ###############################################################
    # BOUNDARY CONDITIONS
    ###############################################################
    print_header("APPLYING BOUNDARY CONDITIONS")

    # 40 mph inlet
    try:
        solver.tui.define.boundary_conditions.velocity_inlet(
            "inlet", "yes", "velocity-magnitude", "40"
        )
        print("[BC] Inlet = 40 mph")
    except:
        print("[BC] ERROR setting inlet velocity")

    # Moving ground
    try:
        solver.tui.define.boundary_conditions.wall(
            "ground", "yes",
            "motion", "moving-wall",
            "moving-wall-speed", "40",
            "moving-wall-direction", "1", "0", "0"
        )
        print("[BC] Ground moving at 40 mph")
    except:
        print("[BC] ERROR setting ground motion")

    # Wheels rotating at 88 rad/s
    wheels = ["fw", "rw", "fwb", "rwb"]
    for w in wheels:
        try:
            solver.tui.define.boundary_conditions.wall(
                w, "yes",
                "motion", "rotational",
                "rotation-rate", "88",
                "rotation-axis-origin", "0", "0", "0",
                "rotation-axis-direction", "0", "1", "0"
            )
            print(f"[BC] Wheel {w} set to 88 rad/s")
        except:
            print(f"[BC] ERROR setting wheel: {w}")

    ###############################################################
    # REFERENCE VALUES (REQUIRED FOR Cd/Cl)
    ###############################################################
    print_header("SETTING REFERENCE VALUES")

    try:
        solver.tui.solve.reference_values.set("velocity", "40")
        solver.tui.solve.reference_values.set("compute-from", "inlet")
        print("[Reference] Reference values set from inlet @ 40 mph")
    except:
        print("[Reference] ERROR setting reference values")

    ###############################################################
    # COMPUTE PROJECTED AREA (METHOD 1)
    ###############################################################
    area = compute_projected_area(solver, outdir)

    ###############################################################
    # SOLVER CONTROLS
    ###############################################################
    print_header("CONFIGURING SOLVER CONTROLS")

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
        print("[Solver] Discretization + relaxation set.")
    except:
        print("[Solver] ERROR setting solver controls.")

    ###############################################################
    # RAMP-UP ITERATIONS
    ###############################################################
    print_header("SOLVER RAMP-UP — PHASE 1 (1000 ITERS)")
    solver.solution.RunCalculation.iterate(1000)
    wait()

    print_header("SOLVER RAMP-UP — PHASE 2 (1000 ITERS)")
    solver.solution.RunCalculation.iterate(1000)
    wait()

    # Enable curvature correction
    print_header("ENABLING CURVATURE CORRECTION (PHASE 3)")
    try:
        solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
        print("[GEKO] Curvature correction enabled.")
    except:
        print("[GEKO] ERROR enabling curvature correction.")

    print_header("SOLVER FULL RUN — PHASE 3 (5000 ITERS)")
    solver.solution.RunCalculation.iterate(5000)
    wait()

    ###############################################################
    # CHECK CONVERGENCE
    ###############################################################
    converged = wait_until_converged(solver, target=1e-4, max_wait=1800)

    ###############################################################
    # AERO COEFFICIENTS
    ###############################################################
    print_header("EXTRACTING AERO COEFFICIENTS")
    cd, cl, scx, scz = extract_aero_coeffs(solver, outdir, area)

    ###############################################################
    # EXPORT CONTOURS
    ###############################################################
    print_header("EXPORTING CONTOURS")
    export_contours(solver, outdir)

    ###############################################################
    # SAVE CASE + DATA
    ###############################################################
    print_header("SAVING CASE & DATA")
    save_case_data(solver, outdir)

    print_header("SOLVER COMPLETE")
    return cd, cl, scx, scz

###########################################################
# ---- MAIN WORKFLOW ----
###########################################################

def main():
    print_header("FSAE CFD AUTOMATION (Complete Pipeline)")

    # -------------------------
    # USER INPUTS
    # -------------------------
    geom_path, sim_name, outdir = ask_user_inputs()

    # -------------------------
    # LAUNCH FLUENT MESHING
    # -------------------------
    print_header("LAUNCHING FLUENT MESHING")

    meshing_session = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.MESHING,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=16,
        dimension=3,
        mpi_type="intel",
    )
    wait()

    # -------------------------
    # RUN MESHING PIPELINE
    # -------------------------
    print_header("STARTING MESHING PIPELINE")

    mesh_file = run_meshing(
        session=meshing_session,
        geom_path=geom_path,
        outdir=outdir
    )

    print_header("MESHING COMPLETE")

    # -------------------------
    # RUN SOLVER
    # -------------------------
    print_header("STARTING SOLVER PIPELINE")

    cd, cl, scx, scz = run_solver(mesh_file, outdir)

    # -------------------------
    # FINAL SUMMARY
    # -------------------------
    print_header("SIMULATION SUMMARY")

    print(f"Simulation name: {sim_name}")
    print(f"Geometry:       {geom_path}")
    print(f"Output folder:  {outdir}")

    print("\nAERO RESULTS:")
    print(f"   Cd  = {cd}")
    print(f"   Cl  = {cl}")
    print(f"   SCx = {scx}")
    print(f"   SCz = {scz}")

    print("\nAll results saved inside:")
    print(f"   {outdir}")

    print("\n==============================")
    print(" CFD RUN COMPLETE — GOOD JOB ")
    print("==============================\n")



###########################################################
# ---- RUN SCRIPT ----
###########################################################

if __name__ == "__main__":
    main()
