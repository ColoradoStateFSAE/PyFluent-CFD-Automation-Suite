# simulation_manager.py
# Ram Racing FSAE Aero Automation Suite
# Sequential queue manager for CFD pipelines

import os
import traceback
import datetime


class SimulationManager:

    def __init__(self):
        self.jobs = []                 # list of job dictionaries
        self.log_callback = None       # GUI log function

    # ------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------
    def log(self, msg):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        text = timestamp + msg
        print(text)

        if self.log_callback:
            self.log_callback(text)

    def set_log_callback(self, callback):
        self.log_callback = callback

    # ------------------------------------------------------------
    # JOB QUEUE METHODS
    # ------------------------------------------------------------
    def add_job(self, job_dict):
        """
        A job looks like:
        {
            "pipeline_class": FrontWingPipeline,
            "geom": "...",
            "outdir": "...",
            "sim_name": "...",
            "L": float,
            "W": float,
            "H": float
        }
        """
        self.jobs.append(job_dict)

    def clear(self):
        self.jobs = []

    # ------------------------------------------------------------
    # MAIN QUEUE EXECUTION
    # ------------------------------------------------------------
    def run_all(self):
        """
        Run all queued CFD jobs sequentially.
        """

        if not self.jobs:
            self.log("No simulations in queue.")
            return

        self.log(f"Starting {len(self.jobs)} queued simulations...")

        for i, job in enumerate(self.jobs, start=1):

            self.log(f"--- Simulation {i}/{len(self.jobs)} ---")
            self.log(f"Preparing: {job['sim_name']}")

            try:
                self.run_single_job(job)

            except Exception as e:
                self.log(f"ERROR during simulation '{job['sim_name']}': {e}")
                self.log(traceback.format_exc())
                continue

        self.log("All queued simulations complete.")

    # ------------------------------------------------------------
    # RUN ONE SIMULATION
    # ------------------------------------------------------------
    def run_single_job(self, job):
        """
        Execute the pipeline for one simulation.
        """

        pipeline_class = job["pipeline_class"]
        geom = job["geom"]
        base_out = job["outdir"]
        name = job["sim_name"]

        L = job["L"]
        W = job["W"]
        H = job["H"]

        # Create the simulation output dir
        outdir = base_out
        os.makedirs(outdir, exist_ok=True)

        self.log(f"Output directory: {outdir}")

        # ----------------------------------
        # Construct pipeline instance
        # ----------------------------------
        pipeline = pipeline_class(
            geom_path=geom,
            sim_dir=outdir,
            L=L,
            W=W,
            H=H
        )

        # ----------------------------------
        # MESHING
        # ----------------------------------
        self.log("Meshing started...")
        mesh_file = pipeline.run_meshing()
        self.log(f"Meshing finished: {mesh_file}")

        # ----------------------------------
        # SOLVER
        # ----------------------------------
        self.log("Solver started...")
        results = pipeline.run_solver(mesh_file)
        self.log("Solver finished.")

        # ----------------------------------
        # REPORT GENERATION
        # ----------------------------------
        self.log("Exporting final PDF report...")
        report = pipeline.export_results(results)
        self.log(f"Report generated: {report}")

        self.log(f"Simulation '{name}' complete.\n")

