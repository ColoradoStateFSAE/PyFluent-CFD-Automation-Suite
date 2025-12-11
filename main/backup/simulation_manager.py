# simulation_manager.py
# Thread-safe job execution manager for PySide6 GUI

import os
import traceback


class SimulationManager:
    """
    Handles CFD job queue and provides logging + progress callbacks.
    Updated for PySide6 QThread-based execution.
    """

    def __init__(self):
        self.jobs = []
        self.log_callback = None
        self.progress_callback = None

    # --------------------------------------------------------------
    # Callback setters
    # --------------------------------------------------------------
    def set_log_callback(self, fn):
        """Assigns logging callback (GUI-safe)."""
        self.log_callback = fn

    def set_progress_callback(self, fn):
        """Assigns progress stage callback (GUI-safe)."""
        self.progress_callback = fn

    # --------------------------------------------------------------
    # Logging utilities
    # --------------------------------------------------------------
    def log(self, msg: str):
        print(msg)
        if self.log_callback:
            self.log_callback(msg)

    def progress(self, stage: int):
        if self.progress_callback:
            self.progress_callback(stage)

    # --------------------------------------------------------------
    # Queue handling
    # --------------------------------------------------------------
    def add_job(self, job_dict):
        """Adds a job to the queue."""
        self.jobs.append(job_dict)

    def clear(self):
        """Clears job queue."""
        self.jobs = []

    # --------------------------------------------------------------
    # Sequential execution (used by QThread)
    # --------------------------------------------------------------
    def run_single_threadsafe(self, job):
        """
        Runs ONE CFD job. Called ONLY inside SimulationWorker::run().
        Returns a dictionary describing outcome.
        """

        sim_name = job["sim_name"]
        self.log(f"===== Starting Simulation: {sim_name} =====")

        try:
            pipeline_class = job["pipeline_class"]

            # Create output folder
            os.makedirs(job["outdir"], exist_ok=True)

            # Instantiate pipeline with injected callbacks
            pipeline = pipeline_class(
                geom_path=job["geom"],
                output_dir=job["outdir"],
                sim_name=sim_name,
                L=job["L"],
                W=job["W"],
                H=job["H"],
                logfn=self.log,
                progressfn=self.progress
            )

            # Execute pipeline
            result = pipeline.run()

            self.log(f"===== Simulation Complete: {sim_name} =====")
            return {
                "success": True,
                "sim_name": sim_name,
                "result": result
            }

        except Exception as e:
            tb = traceback.format_exc()
            self.log(f"ERROR during simulation '{sim_name}': {e}")
            self.log(tb)
            return {
                "success": False,
                "sim_name": sim_name,
                "error": str(e),
                "traceback": tb
            }

    # --------------------------------------------------------------
    # Full queue execution (not used with QThread)
    # --------------------------------------------------------------
    def run_all(self):
        """Legacy mode: synchronous queue execution (blocks GUI)."""
        for job in self.jobs:
            self.run_single_threadsafe(job)
