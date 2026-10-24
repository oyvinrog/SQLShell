"""Responsive, serialized batch refresh with GUI updates on the main thread."""
from sqlshell.folder_sources import in_subtree
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


def is_file_source(source):
    return bool(source) and source not in ('database', 'query_result') and not str(source).startswith('database:')


class RefreshWorker(QThread):
    progress = pyqtSignal(int, str)

    def __init__(self, manager, names, parent=None, folders=None, discover_only=False):
        super().__init__(parent)
        self.manager = manager
        self.names = names
        self.results = []
        self.folders = folders or []
        self.discover_only = discover_only
        self.added = []
        self.scan_errors = []

    def run(self):
        names = list(self.names)
        for key, subtree in self.folders:
            self.progress.emit(0, 'Scanning ' + key)
            try:
                added, errors = self.manager.discover_folder_source(key, subtree)
                self.added.extend(added)
                self.scan_errors.extend(errors)
                if not self.discover_only:
                    names.extend(name for relative, name in
                                 self.manager.folder_sources[key]['members'].items()
                                 if in_subtree(relative, subtree))
            except Exception as exc:
                self.scan_errors.append((key, str(exc)))
        self.names = list(dict.fromkeys(names))
        for index, name in enumerate(self.names):
            self.progress.emit(index, name)
            try:
                success, message = self.manager.reload_table(name)
            except Exception as exc:
                success, message = False, str(exc)
            self.results.append((name, success, message))
        self.progress.emit(len(self.names), '')


class RefreshDialog(QDialog):
    def __init__(self, manager, names, parent, folders=None, discover_only=False):
        super().__init__(parent)
        self.setWindowTitle('Discovering folder tables' if discover_only else 'Refreshing tables')
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        self.label = QLabel('Preparing refresh…')
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(names))
        layout.addWidget(self.progress)
        layout.addWidget(QLabel('Please wait before making other database changes.'))
        self.worker = RefreshWorker(manager, names, self, folders, discover_only)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.accept)

    def update_progress(self, completed, name):
        if name.startswith('Scanning '):
            self.progress.setRange(0, 0)
            self.label.setText(name)
            return
        self.progress.setRange(0, max(1, len(self.worker.names)))
        self.progress.setValue(completed)
        if name:
            self.label.setText(f'Refreshing {completed + 1} of {self.progress.maximum()}: {name}')

    def reject(self):
        # Closing the dialog must not allow concurrent access to the connection.
        if not self.worker.isRunning():
            super().reject()

    def run_refresh(self):
        self.worker.start()
        self.exec()
        self.worker.wait()
        results = self.worker.results
        self.deleteLater()
        return results
