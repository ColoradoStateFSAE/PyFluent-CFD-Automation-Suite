# diagnostics.py
# Fluent Environment Diagnostic Tool for Ram Racing Aero Automation Suite

import os
import subprocess
import ansys.fluent.core as pyfluent


class FluentDiagnostics:
    """
    Performs a full set of Fluent environment checks.
    Used by the GUI to confirm the system is ready for CFD.
    """

    def __init__(self, logfn=None):
        self.log = logfn if logfn else print

        self.results = {
            "AWP_ROOT": False,
            "ANSYS_FLUENT_DIR": False,
            "fluent_in_path": False,
            "fluent_version": None,
            "pyfluent_import": True,
            "fluent_launch": False,
            "notes": []
        }

    # ------------------------------------------------------------
    # Helper for checking environment variables
    # ------------------------------------------------------------
    def check_environment_vars(self):
        awp_root = os.environ.get("AWP_ROOT251") or \
                   os.environ.get("AWP_ROOT") or \
                   os.environ.get("AWP_ROOT252")
        if awp_root:
            self.results["AWP_ROOT"] = True
            self.log(f"[Diagnostics] AWP_ROOT found: {awp_root}")
        else:
            self.log("[Diagnostics] Missing: AWP_ROOT")
            self.results["notes"].append("AWP_ROOT environment variable not set.")

        fluent_dir = os.environ.get("ANSYS_FLUENT_DIR")
        if fluent_dir:
            self.results["ANSYS_FLUENT_DIR"] = True
            self.log(f"[Diagnostics] ANSYS_FLUENT_DIR found: {fluent_dir}")
        else:
            self.log("[Diagnostics] Missing: ANSYS_FLUENT_DIR")
            self.results["notes"].append("ANSYS_FLUENT_DIR not set (required).")

    # ------------------------------------------------------------
    # Check if Fluent is callable from PATH
    # ------------------------------------------------------------
    def check_fluent_in_path(self):
        try:
            subprocess.run(["fluent", "-v"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           timeout=5)
            self.results["fluent_in_path"] = True
            self.log("[Diagnostics] Fluent found in PATH.")
        except Exception:
            self.log("[Diagnostics] Fluent NOT found in PATH.")
            self.results["notes"].append("Fluent is not accessible from PATH.")

    # ------------------------------------------------------------
    # Check Fluent version
    # ------------------------------------------------------------
    def check_fluent_version(self):
        try:
            out = subprocess.run(
                ["fluent", "-v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True
            )
            if out.returncode == 0:
                self.results["fluent_version"] = out.stdout.strip()
                self.log(f"[Diagnostics] Fluent version:\n{out.stdout}")
        except Exception:
            self.log("[Diagnostics] Fluent version check failed.")

    # ------------------------------------------------------------
    # Check PyFluent ability to launch Fluent (no GUI)
    # ------------------------------------------------------------
    def check_fluent_launch(self):
        try:
            self.log("[Diagnostics] Attempting to launch Fluent via PyFluent...")
            sess = pyfluent.launch_fluent(
                mode=pyfluent.FluentMode.SOLVER,
                precision=pyfluent.Precision.DOUBLE,
                processor_count=2,
                dimension=3,
                show_gui=False
            )
            sess.exit()
            self.log("[Diagnostics] Fluent launch successful.")
            self.results["fluent_launch"] = True
        except Exception as e:
            self.log(f"[Diagnostics] Fluent launch failed: {e}")
            self.results["notes"].append("PyFluent could not launch Fluent.")

    # ------------------------------------------------------------
    # Perform all checks
    # ------------------------------------------------------------
    def run_all(self):
        self.log("========== Fluent Diagnostics ==========")

        self.check_environment_vars()
        self.check_fluent_in_path()
        self.check_fluent_version()
        self.check_fluent_launch()

        self.log("========== Diagnostics Complete ==========")
        return self.results
