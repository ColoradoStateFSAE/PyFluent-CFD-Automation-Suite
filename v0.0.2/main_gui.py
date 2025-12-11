# main_gui.py
# Ram Racing FSAE Aero Automation Suite (PySide6)
# Fully threaded GUI with progress bar, theme toggle, and diagnostics

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
    QListWidget, QFormLayout, QVBoxLayout, QHBoxLayout, QFileDialog,
    QMessageBox, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt

from worker_thread import SimulationWorker
from simulation_manager import SimulationManager
from diagnostics import FluentDiagnostics

from frontwing_pipeline import FrontWingPipeline
from rearwing_pipeline import RearWingPipeline
from undertray_pipeline import UndertrayPipeline
from halfcar_pipeline import HalfCarPipeline

# Theme files (inline for simplicity)
LIGHT_STYLESHEET = """
QWidget { background-color: #ffffff; color: #000000; }
QLineEdit, QTextEdit, QListWidget { background-color: #f0f0f0; }
QPushButton { background-color: #e0e0e0; padding: 4px; }
"""

DARK_STYLESHEET = """
QWidget { background-color: #202020; color: #e0e0e0; }
QLineEdit, QTextEdit, QListWidget { background-color: #303030; color: #ffffff; }
QPushButton { background-color: #404040; color: #ffffff; padding: 4px; }
"""


# ===================================================================
# MAIN GUI
# ===================================================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.manager = SimulationManager()
        self.current_worker = None

        self.setWindowTitle("Ram Racing FSAE Aero Automation Suite")
        self.setGeometry(200, 200, 900, 680)

        # Build UI
        self.init_ui()

        # Run Fluent diagnostics on startup
        self.run_diagnostics(show_popup=False)

    # ===========================================================
    # UI LAYOUT
    # ===========================================================
    def init_ui(self):
        layout = QVBoxLayout()

        # -------------------------------------------------------
        # INPUT FIELDS
        # -------------------------------------------------------
        form = QFormLayout()

        self.geom_path = QLineEdit()
        self.out_path = QLineEdit()
        self.sim_name = QLineEdit()

        self.L_field = QLineEdit("3.1")
        self.W_field = QLineEdit("1.40462")
        self.H_field = QLineEdit("1.19507")

        browse_geom = QPushButton("Browse Geometry")
        browse_geom.clicked.connect(self.browse_geometry)

        browse_out = QPushButton("Browse Output Folder")
        browse_out.clicked.connect(self.browse_output)

        form.addRow("Geometry File:", self.geom_path)
        form.addRow("", browse_geom)
        form.addRow("Output Folder:", self.out_path)
        form.addRow("", browse_out)
        form.addRow("Simulation Name:", self.sim_name)

        form.addRow("Length (L):", self.L_field)
        form.addRow("Width (W):", self.W_field)
        form.addRow("Height (H):", self.H_field)

        layout.addLayout(form)

        # -------------------------------------------------------
        # THEME TOGGLE
        # -------------------------------------------------------
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_box = QComboBox()
        self.theme_box.addItems(["Light", "Dark"])
        self.theme_box.currentIndexChanged.connect(self.apply_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_box)
        layout.addLayout(theme_layout)

        # -------------------------------------------------------
        # PIPELINE BUTTONS
        # -------------------------------------------------------
        pipe_layout = QHBoxLayout()

        btn_fw = QPushButton("Run Front Wing")
        btn_rw = QPushButton("Run Rear Wing")
        btn_ut = QPushButton("Run Undertray")
        btn_hc = QPushButton("Run Half-Car")

        btn_fw.clicked.connect(lambda: self.queue_job("fw"))
        btn_rw.clicked.connect(lambda: self.queue_job("rw"))
        btn_ut.clicked.connect(lambda: self.queue_job("ut"))
        btn_hc.clicked.connect(lambda: self.queue_job("hc"))

        pipe_layout.addWidget(btn_fw)
        pipe_layout.addWidget(btn_rw)
        pipe_layout.addWidget(btn_ut)
        pipe_layout.addWidget(btn_hc)

        layout.addLayout(pipe_layout)

        # -------------------------------------------------------
        # QUEUE + CONTROLS
        # -------------------------------------------------------
        queue_ctrl = QHBoxLayout()

        btn_add = QPushButton("Add to Queue Only")
        btn_start = QPushButton("Start Queue")
        btn_diag = QPushButton("Run Diagnostics")

        btn_add.clicked.connect(self.add_to_queue_only)
        btn_start.clicked.connect(self.start_queue)
        btn_diag.clicked.connect(self.run_diagnostics)

        queue_ctrl.addWidget(btn_add)
        queue_ctrl.addWidget(btn_start)
        queue_ctrl.addWidget(btn_diag)

        layout.addLayout(queue_ctrl)

        # -------------------------------------------------------
        # LOG WINDOW
        # -------------------------------------------------------
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        # -------------------------------------------------------
        # QUEUE LIST
        # -------------------------------------------------------
        self.queue_list = QListWidget()
        layout.addWidget(self.queue_list)

        # -------------------------------------------------------
        # PROGRESS BAR + LABEL
        # -------------------------------------------------------
        self.progress_label = QLabel("Idle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

        # Default to dark theme (recommended for engineering apps)
        self.apply_theme()

    # ===========================================================
    # FILE BROWSING
    # ===========================================================
    def browse_geometry(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Geometry File", "", "CAD Files (*.stp *.step *.igs *.iges)"
        )
        if file:
            self.geom_path.setText(file)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.out_path.setText(folder)

    # ===========================================================
    # QUEUE HANDLING
    # ===========================================================
    def queue_job(self, pipeline_type):
        job = self.build_job(pipeline_type)
        if job:
            self.manager.add_job(job)
            self.queue_list.addItem(f"{job['sim_name']} ({pipeline_type.upper()})")
            self.log(f"Queued: {job['sim_name']}")

    def add_to_queue_only(self):
        QMessageBox.information(self, "Queue", "Job added to queue.")

    def start_queue(self):
        if not self.manager.jobs:
            self.error("No jobs in queue.")
            return

        self.start_next_job()

    def start_next_job(self):
        """Runs the next CFD job using QThread."""
        if not self.manager.jobs:
            self.log("All queued jobs completed.")
            self.progress_label.setText("Complete")
            self.progress_bar.setValue(100)
            return

        job = self.manager.jobs.pop(0)

        self.log(f"Starting job: {job['sim_name']}")
        self.progress_label.setText("Starting...")
        self.progress_bar.setValue(0)

        self.current_worker = SimulationWorker(job, self.manager)
        self.current_worker.log_signal.connect(self.log)
        self.current_worker.progress_signal.connect(self.update_progress)
        self.current_worker.finished_signal.connect(self.job_finished)
        self.current_worker.error_signal.connect(self.error)

        self.current_worker.start()

    def job_finished(self, result):
        sim = result["sim_name"]
        self.log(f"Job complete: {sim}")
        self.start_next_job()

    # ===========================================================
    # PROGRESS HANDLING
    # ===========================================================
    def update_progress(self, stage):
        stage_map = {
            0: ("Starting...", 0),
            1: ("Surface Mesh Complete", 15),
            2: ("Volume Mesh Complete", 35),
            3: ("Solver Ramp 1", 55),
            4: ("Solver Ramp 2 (Curvature ON)", 75),
            5: ("Solver Ramp 3", 90),
            6: ("Report Generation Complete", 100),
        }

        label, pct = stage_map.get(stage, ("Unknown", 0))

        self.progress_label.setText(label)
        self.progress_bar.setValue(pct)

    # ===========================================================
    # JOB CREATION
    # ===========================================================
    def build_job(self, ptype):
        geom = self.geom_path.text().strip()
        outdir = self.out_path.text().strip()
        name = self.sim_name.text().strip()

        if not geom or not os.path.exists(geom):
            return self.error("Invalid geometry file.")
        if not outdir or not os.path.exists(outdir):
            return self.error("Invalid output folder.")
        if not name:
            return self.error("Simulation name required.")

        L = float(self.L_field.text())
        W = float(self.W_field.text())
        H = float(self.H_field.text())

        pipe_map = {
            "fw": FrontWingPipeline,
            "rw": RearWingPipeline,
            "ut": UndertrayPipeline,
            "hc": HalfCarPipeline,
        }

        if ptype not in pipe_map:
            return self.error(f"Unknown pipeline type {ptype}")

        return {
            "pipeline_class": pipe_map[ptype],
            "geom": geom,
            "outdir": os.path.join(outdir, name),
            "sim_name": name,
            "L": L,
            "W": W,
            "H": H
        }

    # ===========================================================
    # THEME SYSTEM
    # ===========================================================
    def apply_theme(self):
        theme = self.theme_box.currentText()
        if theme == "Light":
            self.setStyleSheet(LIGHT_STYLESHEET)
        else:
            self.setStyleSheet(DARK_STYLESHEET)

    # ===========================================================
    # DIAGNOSTICS
    # ===========================================================
    def run_diagnostics(self, show_popup=True):
        diag = FluentDiagnostics(logfn=self.log)
        results = diag.run_all()

        if show_popup:
            if results["fluent_launch"]:
                QMessageBox.information(self, "Diagnostics", "Fluent environment OK.")
            else:
                QMessageBox.warning(
                    self, "Diagnostics",
                    "Warning: Fluent cannot be launched.\nCheck installation."
                )

    # ===========================================================
    # LOGGING
    # ===========================================================
    def log(self, msg):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.log(f"ERROR: {msg}")
        return None


# ===================================================================
# MAIN ENTRY
# ===================================================================
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
