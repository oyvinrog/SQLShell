"""Folder-source UI orchestration. Data discovery is run by RefreshDialog."""
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QListWidget,
                            QListWidgetItem, QMenu, QTreeWidgetItem, QVBoxLayout,
                            QLabel, QMessageBox)
from sqlshell.refresh_dialog import RefreshDialog

SOURCE_ROLE = Qt.ItemDataRole.UserRole + 10
RELATIVE_ROLE = Qt.ItemDataRole.UserRole + 11


def source_icon():
    return QIcon(str(Path(__file__).parent / 'resources' / 'folder_source.svg'))


def source_item_info(item):
    if item is None:
        return None
    key = item.data(0, SOURCE_ROLE)
    return (key, item.data(0, RELATIVE_ROLE) or '') if key else None


class FolderSourceWindowMixin:
    def browse_folder_source(self):
        if getattr(self, '_refresh_in_progress', False):
            return
        path = QFileDialog.getExistingDirectory(self, 'Add Folder Source')
        if path:
            self.add_folder_source(path)

    def add_folder_source(self, path):
        key = self.db_manager.add_folder_source(path)
        for i in range(self.tables_list.topLevelItemCount()):
            item = self.tables_list.topLevelItem(i)
            if source_item_info(item) == (key, ''):
                self.tables_list.setCurrentItem(item)
                item.setExpanded(True)
                return
        self.discover_folder_sources([(key, '')])

    def discover_folder_sources(self, folders):
        """Register paths only. No data readers run when adding/restoring a source."""
        if getattr(self, '_refresh_in_progress', False):
            return
        self._refresh_in_progress = True
        self.update_refresh_controls()
        try:
            dialog = RefreshDialog(self.db_manager, [], self, folders=folders, discover_only=True)
            dialog.run_refresh()
            self.sync_folder_source_tree(dialog.worker.added)
        finally:
            self._refresh_in_progress = False
            self.update_refresh_controls()
        self.update_completer()
        self.statusBar().showMessage(
            f'{len(dialog.worker.added)} tables discovered; data loads when used.')
        if dialog.worker.scan_errors:
            self.show_refresh_failures('Folder scan incomplete',
                [f'{path}: {message}' for path, message in dialog.worker.scan_errors])

    def sync_folder_source_tree(self, pending=()):
        tree = self.tables_list
        tree.tables_needing_reload.update(pending)
        for key, source in self.db_manager.folder_sources.items():
            folders = {}
            stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
            while stack:
                item = stack.pop()
                info = source_item_info(item)
                if info and info[0] == key and tree.is_folder_item(item):
                    folders[info[1]] = item
                stack.extend(item.child(i) for i in range(item.childCount()))
            if '' not in folders:
                root = tree.create_folder(Path(source['path']).name or source['path'])
                root.setData(0, SOURCE_ROLE, key)
                root.setData(0, RELATIVE_ROLE, '')
                folders[''] = root
            for relative, folder in folders.items():
                folder.setFlags(folder.flags() & ~Qt.ItemFlag.ItemIsDropEnabled & ~Qt.ItemFlag.ItemIsDragEnabled)
                folder.setToolTip(0, str(Path(source['path']) / relative))
            root = folders['']
            root.setIcon(0, source_icon())
            root.setToolTip(0, source['path'] + '\nFolder source • data loads when used')
            root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsDropEnabled & ~Qt.ItemFlag.ItemIsDragEnabled)
            for relative, name in sorted(source['members'].items()):
                parent = root
                parts = Path(relative).parts[:-1]
                for depth, part in enumerate(parts):
                    subpath = '/'.join(parts[:depth + 1])
                    if subpath not in folders:
                        folder = QTreeWidgetItem(parent)
                        folder.setText(0, part)
                        folder.setData(0, Qt.ItemDataRole.UserRole, 'folder')
                        folder.setData(0, SOURCE_ROLE, key)
                        folder.setData(0, RELATIVE_ROLE, subpath)
                        folder.setIcon(0, QIcon.fromTheme('folder', source_icon()))
                        folder.setToolTip(0, str(Path(source['path']) / subpath))
                        folder.setFlags(folder.flags() & ~Qt.ItemFlag.ItemIsDropEnabled & ~Qt.ItemFlag.ItemIsDragEnabled)
                        folders[subpath] = folder
                    parent = folders[subpath]
                item = tree.find_table_item(name)
                if item is None:
                    item = tree.add_table_item(name, Path(relative).name,
                                              needs_reload=name in tree.tables_needing_reload)
                if item.parent() is not parent:
                    if item.parent():
                        item.parent().removeChild(item)
                    else:
                        tree.takeTopLevelItem(tree.indexOfTopLevelItem(item))
                    parent.addChild(item)
                item.setData(0, SOURCE_ROLE, key)
                item.setData(0, RELATIVE_ROLE, relative)
                path = str(Path(source['path']) / relative)
                item.setToolTip(0, path + ('\nLoads when used' if name in tree.tables_needing_reload else ''))
                if not os.path.exists(path):
                    tree.mark_table_failed(name, 'Source is missing; any previous data is stale.')

    def folder_source_context_menu(self, item, position):
        key, relative = source_item_info(item)
        menu = QMenu(self)
        refresh = menu.addAction('Refresh Folder')
        restore = remove = None
        if not relative:
            restore = menu.addAction('Restore Excluded Files…')
            restore.setEnabled(bool(self.db_manager.folder_sources[key]['excluded']))
            remove = menu.addAction('Remove Folder Source')
        action = menu.exec(self.tables_list.viewport().mapToGlobal(position))
        if action == refresh:
            selection = self.tables_list.selectedItems()
            self.reload_selected_tables(selection if item in selection else [item])
        elif restore is not None and action == restore:
            self.restore_excluded_files(key)
        elif remove is not None and action == remove:
            self.remove_folder_source(key)

    def restore_excluded_files(self, key):
        source = self.db_manager.folder_sources[key]
        dialog = QDialog(self)
        dialog.setWindowTitle('Restore Excluded Files')
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Select files to make available again. Data loads when used.'))
        choices = QListWidget()
        for relative in source['excluded']:
            item = QListWidgetItem(relative, choices)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
        layout.addWidget(choices)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            restored = {choices.item(i).text() for i in range(choices.count())
                        if choices.item(i).checkState() == Qt.CheckState.Checked}
            source['excluded'] = [p for p in source['excluded'] if p not in restored]
            self.discover_folder_sources([(key, '')])

    def remove_folder_source(self, key):
        if QMessageBox.question(self, 'Remove Folder Source',
                'Remove this source and its tables from the project? Files on disk are kept.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        source = self.db_manager.folder_sources[key]
        failures = []
        for name in list(source['members'].values()):
            if self.db_manager.remove_table(name):
                self.tables_list.tables_needing_reload.discard(name)
                item = self.tables_list.find_table_item(name)
                if item and item.parent():
                    item.parent().removeChild(item)
            else:
                failures.append(name)
        if failures:
            self.show_refresh_failures('Could not remove all tables', failures)
            return
        del self.db_manager.folder_sources[key]
        for i in range(self.tables_list.topLevelItemCount() - 1, -1, -1):
            if source_item_info(self.tables_list.topLevelItem(i)) == (key, ''):
                self.tables_list.takeTopLevelItem(i)
        self.update_completer()
        self.update_refresh_controls()
