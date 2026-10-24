"""Responsive, serialized batch refresh with GUI updates on the main thread."""
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


def is_file_source(source):
    return bool(source) and source not in ('database', 'query_result') and not str(source).startswith('database:')


class RefreshWorker(QThread):
    progress = pyqtSignal(int, str)

    def __init__(self, manager, names, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.names = names
        self.results = []

    def run(self):
        for index, name in enumerate(self.names):
            self.progress.emit(index, name)
            try:
                success, message = self.manager.reload_table(name)
            except Exception as exc:
                success, message = False, str(exc)
            self.results.append((name, success, message))
        self.progress.emit(len(self.names), '')


class RefreshDialog(QDialog):
    def __init__(self, manager, names, parent):
        super().__init__(parent)
        self.setWindowTitle('Refreshing tables')
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        self.label = QLabel('Preparing refresh…')
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(names))
        layout.addWidget(self.progress)
        layout.addWidget(QLabel('Please wait before making other database changes.'))
        self.worker = RefreshWorker(manager, names, self)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.accept)

    def update_progress(self, completed, name):
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
