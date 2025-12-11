# worker_thread.py
# QThread-based simulation worker for PySide6 GUI

from PySide6.QtCore import QThread, Signal
import traceback


class SimulationWorker(QThread):
    # Signals emitted to the GUI
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, job, manager):
        super().__init__()
        self.job = job
        self.manager = manager

    # Allow pipelines to log back into the GUI
    def log(self, msg: str):
        self.log_signal.emit(msg)

    # Allow pipelines to send progress stage number (0–6)
    def progress(self, stage: int):
        self.progress_signal.emit(stage)

    def run(self):
        """
        Executes one CFD pipeline job in a safe thread.
        """
        try:
            # Inject log + progress callbacks into manager
            self.manager.set_log_callback(self.log)
            self.manager.set_progress_callback(self.progress)

            # Execute the job
            result = self.manager.run_single_threadsafe(self.job)

            # Emit finish event
            self.finished_signal.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            self.error_signal.emit(f"{str(e)}\n\n{tb}")
