# worker_thread.py
# QThread-based simulation worker for PySide6 GUI
# Updated: adds CPU-core control + safe session launch + clean logging

from PySide6.QtCore import QThread, Signal
import traceback


class SimulationWorker(QThread):
    # Signals emitted back to the GUI threads
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, job, manager, ncores=60):
        """
        job: job dictionary from GUI
        manager: SimulationManager instance
        ncores: number of Fluent solver cores to launch
        """
        super().__init__()
        self.job = job
        self.manager = manager
        self.ncores = ncores

    # ------------------------------------------------------
    # Pipeline → GUI logging bridge
    # ------------------------------------------------------
    def log(self, msg):
        self.log_signal.emit(msg)

    def progress(self, stage):
        self.progress_signal.emit(stage)

    # ------------------------------------------------------
    # Main threaded execution
    # ------------------------------------------------------
    def run(self):
        """
        Executed inside worker thread — safe for long CFD tasks.
        """
        try:
            # Inject callbacks into the manager (these propagate to pipelines)
            self.manager.set_log_callback(self.log)
            self.manager.set_progress_callback(self.progress)

            # Tell the SimulationManager how many Fluent cores to use
            self.manager.set_core_count(self.ncores)

            # Execute one CFD job in isolation
            result = self.manager.run_single_threadsafe(self.job)

            # Notify GUI job finished
            self.finished_signal.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            self.error_signal.emit(f"Exception in worker:\n{e}\n\n{tb}")
