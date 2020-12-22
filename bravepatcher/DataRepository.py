import tempfile
from pathlib import Path

import appdirs


class DataRepository:
    app_name = "BravePatcher"
    author = "Maxisoft"

    def __init__(self):
        self.data_dir = Path(appdirs.user_data_dir(self.app_name, self.author))
        self.config_dir = Path(appdirs.user_config_dir(self.app_name, self.author))

    def _create_directories(self):
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)

    @property
    def pattern_data_path(self) -> Path:
        self._create_directories()
        return Path(self.data_dir, "patterns.json")

    @property
    def chrome_backup(self):
        self._create_directories()
        return Path(self.data_dir, "chrome.dll.tar.gz")

    @property
    def chrome_backup_json(self):
        self._create_directories()
        return Path(self.data_dir, "chrome.dll.json")

    @property
    def patch_results_json(self):
        self._create_directories()
        return Path(self.data_dir, "patch_results.json")

    def create_tmp_dir(self, suffix='') -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory(prefix=self.app_name, suffix=suffix)