# main_gui.py
# Ram Racing FSAE Aero Automation Suite
# GUI interface for running isolated and half-car CFD pipelines

import sys
import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from simulation_manager import SimulationManager
from pipelines import (
    FrontWingPipeline,
    RearWingPipeline,
    UndertrayPipeline,
    HalfCarPipeline,
)


class MainWindow(QtWidgets.QWidget):
    """
    Main application window for the CFD automation suite.
    """

    def __init__(self):
        super().__init__()

        # --------------------------
        # Declare all attributes here
        # --------------------------
        self.geom_path: QtWidgets.QLineEdit = None
        self.out_path: QtWidgets.QLineEdit = None
        self.sim_name: QtWidgets.QLineEdit = None

        self.L_field: QtWidgets.QLineEdit = None
        self.W_field: QtWidgets.QLineEdit = None
        self.H_field: QtWidgets.QLineEdit = None

        self.btn_fw: QtWidgets.QPushButton = None
        self.btn_rw: QtWidgets.QPushButton = None
        self.btn_ut: QtWidgets.QPushButton = None
        self.btn_hc: QtWidgets.QPushButton = None

        self.log_box: QtWidgets.QTextEdit = None
        self.queue_list: QtWidgets.QListWidget = None

        # Backend simulation manager
        self.manager = SimulationManager()

        # Window setup
        self.setWindowTitle("Ram Racing FSAE Aero Automation Suite")
        self.setGeometry(200, 200, 850, 600)

        # Build GUI
        self.init_ui()

    # ============================================================
    # GUI Layout
    # ============================================================
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()

        # --------------------------
        # Input fields
        # --------------------------
        self.geom_path = QtWidgets.QLineEdit()
        self.out_path = QtWidgets.QLineEdit()
        self.sim_name = QtWidgets.QLineEdit()

        self.L_field = QtWidgets.QLineEdit("3.1")
        self.W_field = QtWidgets.QLineEdit("1.40462")
        self.H_field = QtWidgets.QLineEdit("1.19507")

        browse_geom = QtWidgets.QPushButton("Browse Geometry")
        browse_geom.clicked.connect(self.browse_geometry)

        browse_out = QtWidgets.QPushButton("Browse Output")
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

        # --------------------------
        # Pipeline buttons
        # --------------------------
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_fw = QtWidgets.QPushButton("Run Front Wing")
        self.btn_rw = QtWidgets.QPushButton("Run Rear Wing")
        self.btn_ut = QtWidgets.QPushButton("Run Undertray")
        self.btn_hc = QtWidgets.QPushButton("Run Half Car")

        self.btn_fw.clicked.connect(lambda: self.add_job("fw"))
        self.btn_rw.clicked.connect(lambda: self.add_job("rw"))
        self.btn_ut.clicked.connect(lambda: self.add_job("ut"))
        self.btn_hc.clicked.connect(lambda: self.add_job("hc"))

        btn_layout.addWidget(self.btn_fw)
        btn_layout.addWidget(self.btn_rw)
        btn_layout.addWidget(self.btn_ut)
        btn_layout.addWidget(self.btn_hc)

        layout.addLayout(btn_layout)

        # --------------------------
        # Queue controls
        # --------------------------
        queue_controls = QtWidgets.QHBoxLayout()

        add_queue = QtWidgets.QPushButton("Add to Queue Only")
        start_queue = QtWidgets.QPushButton("Start Queue")

        add_queue.clicked.connect(self.add_to_queue_only)
        start_queue.clicked.connect(self.start_queue)

        queue_controls.addWidget(add_queue)
        queue_controls.addWidget(start_queue)

        layout.addLayout(queue_controls)

        # --------------------------
        # Log window
        # --------------------------
        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        # --------------------------
        # Queue display
        # --------------------------
        self.queue_list = QtWidgets.QListWidget()
        layout.addWidget(self.queue_list)

        self.setLayout(layout)

    # ============================================================
    # Handlers
    # ============================================================
    def browse_geometry(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Select Geometry File",
            "",
            "CAD Files (*.stp *.step *.igs *.iges)"
        )
        if fname:
            self.geom_path.setText(fname)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder"
        )
        if folder:
            self.out_path.setText(folder)

    def add_job(self, pipeline_name: str):
        job = self.build_job(pipeline_name)
        if job:
            self.manager.add_job(job)
            self.queue_list.addItem(f"Queued: {job['sim_name']} ({pipeline_name.upper()})")

    def add_to_queue_only(self):
        QMessageBox.information(self, "Queue", "Simulation added to queue. Press 'Start Queue' to run.")

    def start_queue(self):
        self.log("Starting simulation queue...")
        self.manager.set_log_callback(self.log)
        self.manager.run_all()
        self.log("Queue finished.")

    def build_job(self, sim_type: str):
        geom = self.geom_path.text().strip()
        outdir = self.out_path.text().strip()
        name = self.sim_name.text().strip()

        if not geom or not os.path.exists(geom):
            return self.error("Geometry file invalid.")

        if not outdir or not os.path.exists(outdir):
            return self.error("Output folder invalid.")

        if not name:
            return self.error("Simulation name required.")

        try:
            L = float(self.L_field.text())
            W = float(self.W_field.text())
            H = float(self.H_field.text())
        except ValueError:
            return self.error("L, W, H must be numeric.")

        pipeline_map = {
            "fw": FrontWingPipeline,
            "rw": RearWingPipeline,
            "ut": UndertrayPipeline,
            "hc": HalfCarPipeline,
        }

        if sim_type not in pipeline_map:
            return self.error("Unknown simulation type.")

        job = {
            "pipeline_class": pipeline_map[sim_type],
            "geom": geom,
            "outdir": os.path.join(outdir, name),
            "sim_name": name,
            "L": L,
            "W": W,
            "H": H,
        }

        return job

    # ============================================================
    # Logging utilities
    # ============================================================
    def log(self, msg: str):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    def error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)
        self.log(f"ERROR: {msg}")
        return None


# ======================================================================
# MAIN
# ======================================================================
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
