##############################################
# FSAE REAR WING CFD AUTOMATION SCRIPT
# Full Meshing + Solver Pipeline
# Fluent 2025R2 — Watertight Geometry Workflow
# Isolated Rear Wing Geometry (No Wheels)
##############################################

import os
import time
import math
import ansys.fluent.core as pyfluent


###########################################################
# ---- USER INPUT INTERFACE ----
###########################################################

def ask_user_inputs():
    print("\n===========================================")
    print("      FSAE CFD AUTOMATION — REAR WING")
    print("===========================================\n")

    geom = input("Enter full path to REAR WING geometry (.step or .stp): ").strip()
    while not os.path.isfile(geom):
        geom = input("❗ File not found. Enter geometry file path again: ").strip()

    sim_name = input("Enter simulation name (e.g., RW_test01): ").strip()
    if sim_name == "":
        sim_name = "rearwing_sim"

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
# ---- RESIDUAL MONITOR ----
###########################################################

def get_continuity_residual(solver):
    try:
        res = solver.solution.Monitors.Residual.GetValues()
        return res.get("continuity", None)
    except:
        return None


def wait_until_converged(solver, target=1e-4, max_wait=1800):
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
# ---- SAVE CASE/DATA ----
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
# ---- PROJECTED AREA ----
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

        print("\n[Aero Results — REAR WING]")
        print(f"   Cd  = {cd}")
        print(f"   Cl  = {cl}")
        print(f"   SCx = {scx}")
        print(f"   SCz = {scz}\n")

        return cd, cl, scx, scz

    except:
        print("[Aero] ERROR extracting aero coefficients.")
        return None, None, None, None

###########################################################
# ---- MESHING PIPELINE (REAR WING) ----
###########################################################

def run_meshing(session, geom_path, outdir, L, W, H):
    workflow = session.workflow
    tasks = workflow.TaskObject

    print_header("IMPORTING GEOMETRY")

    # -------------------------------
    # 1. Import Geometry
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

    # Fine mesh preset
    near_size = 0.016
    mid_size  = 0.032
    far_size  = 0.064

    # Symmetric half-model (Z-direction)
    zmin = 0
    zmax = W * 0.5

    # Scaled refinement boxes using L/W/H supplied by user
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

    # Create refinement regions
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
    # CURVATURE SIZING (Rear Wing Only)
    ###############################################################

    print_header("APPLYING CURVATURE SIZING TO REAR WING")

    add_sizing = tasks["Add Local Sizing"]

    # Only one curvature sizing group needed
    add_sizing.AddChildToTask()
    child = tasks["curvature_aero"]
    child.Arguments.set_state({
        "LocalSizingType": "Curvature",
        "SizeControlType": "Curvature",
        "MinSize": 0.0005,
        "MaxSize": 0.008,
        "CurvatureNormalAngle": 9,
        "BoundaryNameList": ["rearwing"]
    })
    child.Execute()
    wait()


    ###############################################################
    # SURFACE MESH GENERATION
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


    ###############################################################
    # SURFACE MESH IMPROVEMENT
    ###############################################################

    print_header("IMPROVING SURFACE MESH")

    improve_surf = tasks["Improve Surface Mesh"]
    improve_surf.Arguments.set_state({
        "FaceQualityLimit": 0.7
    })
    improve_surf.Execute()
    wait()


    ###############################################################
    # DESCRIBE GEOMETRY — FLUID ONLY
    ###############################################################

    desc = tasks["Describe Geometry"]
    desc.Arguments.set_state({
        "SetupType": "The geometry consists of only fluid regions with no voids"
    })
    desc.Execute()
    wait()


    ###############################################################
    # UPDATE BOUNDARIES + REGIONS
    ###############################################################

    tasks["Update Boundaries"].Execute()
    wait()

    tasks["Update Regions"].Execute()
    wait()


    ###############################################################
    # BOUNDARY LAYERS (Rear Wing Only)
    ###############################################################

    print_header("ADDING BOUNDARY LAYERS — REAR WING")

    bl = tasks["Add Boundary Layers"]
    bl.AddChildToTask()
    child = tasks["last-ratio_1"]

    child.Arguments.set_state({
        "BoundaryZones": ["rearwing"],
        "FirstLayerHeight": 0.0005,
        "NumberOfLayers": 10,
        "LastLayerRatio": 1.2
    })
    child.Execute()
    wait()


    ###############################################################
    # VOLUME MESHING — POLY-HEXCORE
    ###############################################################

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


    ###############################################################
    # VOLUME MESH IMPROVEMENT
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

    mesh_out = os.path.join(outdir, "mesh_rearwing.msh.h5")
    try:
        session.meshing.SaveMesh(file_name=mesh_out)
        print(f"[Mesh] Final REAR WING mesh saved → {mesh_out}")
    except Exception as e:
        print(f"[Mesh] ERROR saving mesh: {e}")

    return mesh_out

###########################################################
# ---- SOLVER PIPELINE (REAR WING) ----
###########################################################

def run_solver(mesh_path, outdir):
    print_header("LAUNCHING FLUENT SOLVER (REAR WING)")

    solver = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.SOLVER,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=16,
        dimension=3,
        mpi_type="intel",
    )
    wait()

    # -------------------------------
    # LOAD MESH
    # -------------------------------
    print("[Solver] Loading mesh...")
    solver.solver.File.Read(file_type="mesh", file_name=mesh_path)
    wait()


    ###############################################################
    # SET UNITS
    ###############################################################
    print_header("SETTING UNITS → lbf, mph")
    try:
        solver.tui.define.units("force", "lbf")
        solver.tui.define.units("velocity", "mph")
    except:
        print("[Units] Error assigning units.")


    ###############################################################
    # ENABLE GEKO TURBULENCE MODEL
    ###############################################################
    print_header("ENABLING GEKO TURBULENCE MODEL")
    try:
        solver.tui.define.models.viscous.ke_gko("yes")
        solver.tui.define.models.viscous.ke_gko.options.production_limiter("yes")
        solver.tui.define.models.viscous.ke_gko.options.curvature_correction("no")
        print("[Turbulence] GEKO enabled (curvature correction OFF)")
    except:
        print("[Turbulence] ERROR enabling GEKO")


    ###############################################################
    # BOUNDARY CONDITIONS
    ###############################################################
    print_header("APPLYING BOUNDARY CONDITIONS (REAR WING RUN)")

    # 40 mph inlet
    try:
        solver.tui.define.boundary_conditions.velocity_inlet(
            "inlet", "yes", "velocity-magnitude", "40"
        )
        print("[BC] inlet = 40 mph")
    except:
        print("[BC] ERROR applying inlet")

    # Moving ground
    try:
        solver.tui.define.boundary_conditions.wall(
            "ground", "yes",
            "motion", "moving-wall",
            "moving-wall-speed", "40",
            "moving-wall-direction", "1", "0", "0"
        )
        print("[BC] ground = moving at 40 mph")
    except:
        print("[BC] ERROR applying ground motion")

    # No wheels
    print("[BC] Wheels ignored (isolated rear wing geometry)")


    ###############################################################
    # REFERENCE VALUES
    ###############################################################
    print_header("SETTING REFERENCE VALUES")

    try:
        solver.tui.solve.reference_values.set("velocity", "40")
        solver.tui.solve.reference_values.set("compute-from", "inlet")
        print("[Reference] Using inlet reference")
    except:
        print("[Reference] ERROR setting reference values")


    ###############################################################
    # PROJECTED AREA CALCULATION
    ###############################################################
    print_header("COMPUTING PROJECTED FRONTAL AREA")
    area = compute_projected_area(solver, outdir)


    ###############################################################
    # DISCRETIZATION SCHEMES
    ###############################################################
    print_header("SETTING DISCRETIZATION SCHEMES")

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
            "turb-diss-rate", "0.3",
        )

    except:
        print("[Solver] ERROR setting discretization or relaxation factors")


    ###############################################################
    # RAMP-UP SOLVER PHASES
    ###############################################################

    print_header("RAMP-UP PHASE 1 → 1000 ITERATIONS")
    solver.solution.RunCalculation.iterate(1000)
    wait()

    print_header("RAMP-UP PHASE 2 → 1000 ITERATIONS")
    solver.solution.RunCalculation.iterate(1000)
    wait()

    # Turn ON curvature correction for final ramp
    print_header("ENABLING GEKO CURVATURE CORRECTION FOR FINAL RUN")
    try:
        solver.tui.define.models.viscous.ke_gko.options.curvature_correction("yes")
    except:
        print("[GEKO] ERROR enabling curvature correction")

    print_header("FINAL RUN → 5000 ITERATIONS")
    solver.solution.RunCalculation.iterate(5000)
    wait()


    ###############################################################
    # CONVERGENCE CHECK
    ###############################################################
    print_header("CHECKING CONTINUITY RESIDUAL")

    converged = wait_until_converged(solver, 1e-4, 1800)


    ###############################################################
    # REAR WING AERO COEFFICIENTS
    ###############################################################
    print_header("EXTRACTING REAR WING AERO COEFFICIENTS")

    cd, cl, scx, scz = extract_aero_coeffs(
        solver=solver,
        outdir=outdir,
        area=area
    )


    ###############################################################
    # CONTOURS
    ###############################################################
    print_header("EXPORTING CONTOURS")
    export_contours(solver, outdir)


    ###############################################################
    # SAVE CASE & DATA
    ###############################################################
    print_header("SAVING CASE & DATA")
    save_case_data(solver, outdir)


    print_header("SOLVER COMPLETE — REAR WING FINISHED")
    return cd, cl, scx, scz

###########################################################
# ---- MAIN WORKFLOW (REAR WING) ----
###########################################################

def main():
    print_header("FSAE REAR WING CFD — FULL AUTOMATION")

    # ------------------------------------------
    # USER INPUT
    # ------------------------------------------
    geom_path, sim_name, outdir, L, W, H = ask_user_inputs()

    # ------------------------------------------
    # START MESHER
    # ------------------------------------------
    print_header("LAUNCHING FLUENT MESHING SESSION")

    meshing_session = pyfluent.launch_fluent(
        mode=pyfluent.FluentMode.MESHING,
        precision=pyfluent.Precision.DOUBLE,
        processor_count=16,
        dimension=3,
        mpi_type="intel",
    )
    wait()

    # ------------------------------------------
    # RUN MESHING PIPELINE
    # ------------------------------------------
    print_header("RUNNING REAR WING MESHING PIPELINE")

    mesh_file = run_meshing(
        session=meshing_session,
        geom_path=geom_path,
        outdir=outdir,
        L=L, W=W, H=H
    )

    print_header("MESHING COMPLETE — MOVING TO SOLVER")


    # ------------------------------------------
    # SOLVER PIPELINE
    # ------------------------------------------
    cd, cl, scx, scz = run_solver(
        mesh_path=mesh_file,
        outdir=outdir
    )


    # ------------------------------------------
    # SUMMARY OUTPUT
    # ------------------------------------------
    print_header("REAR WING CFD — SUMMARY")

    print(f"Simulation Name:   {sim_name}")
    print(f"Geometry Used:     {geom_path}")
    print(f"Output Folder:     {outdir}\n")

    print("AERODYNAMIC RESULTS (REAR WING):")
    print(f"   Cd  = {cd}")
    print(f"   Cl  = {cl}")
    print(f"   SCx = {scx}")
    print(f"   SCz = {scz}\n")

    print("===============================================")
    print("     REAR WING SIMULATION COMPLETE ✔")
    print("===============================================\n")



###########################################################
# ---- ENTRY POINT ----
###########################################################

if __name__ == "__main__":
    main()
