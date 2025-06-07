import os
import json
from PyQt5.QtCore import QObject, pyqtSignal


class AppSettings(QObject):
    settings_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.possible_modes = ["single", "multiple"]
        self.filename = os.path.join("config", "settings.json")

        # Значения по умолчанию
        self.threshold = 0.8
        self.mode = "multiple"
        self.open_time = 10.0
        self.wait_time = 10

        if os.path.isfile(self.filename):
            self.load()
        else:
            self.save()

    def change_settings(self, ntresh, nmode, nopentime, nwitetime):
        if not isinstance(ntresh, float) or not (0 < ntresh < 2.5):
            raise ValueError("Threshold must be a float between 0 and 2.5")
        if not isinstance(nmode, str) or nmode not in self.possible_modes:
            raise ValueError("Mode must be one of: " + ", ".join(self.possible_modes))
        if not isinstance(nopentime, float) or nopentime <= 0:
            raise ValueError("Open time must be a positive float")
        if not isinstance(nwitetime, int) or nwitetime <= 0:
            raise ValueError("Wait time must be a positive integer")

        self.threshold = ntresh
        self.mode = nmode
        self.open_time = nopentime
        self.wait_time = nwitetime
        self.save()

    def load(self):
        with open(self.filename, 'r') as f:
            obj = json.load(f)
            self.threshold = obj.get("recognition_threshold", self.threshold)
            self.mode = obj.get("working_mode", self.mode)
            self.open_time = obj.get("open_time", self.open_time)
            self.wait_time = obj.get("wait_time", self.wait_time)

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump({
                "recognition_threshold": self.threshold,
                "working_mode": self.mode,
                "wait_time": self.wait_time,
                "open_time": self.open_time
            }, f, indent=4)
        print("Settings saved")
        self.settings_changed.emit()