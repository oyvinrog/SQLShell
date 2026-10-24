"""Regression coverage for sidebar batch refresh."""
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QMenu

from sqlshell import __main__ as main
from sqlshell.table_list import DraggableTablesList

pytestmark = pytest.mark.gui


class RefreshWindow(QMainWindow):
    show_tables_context_menu = main.SQLShell.show_tables_context_menu
    reload_selected_tables = main.SQLShell.reload_selected_tables
    reload_all_tables = main.SQLShell.reload_all_tables
    create_tables_header = main.SQLShell.create_tables_header
    update_refresh_controls = main.SQLShell.update_refresh_controls

    def __init__(self):
        super().__init__()
        self.tables_list = DraggableTablesList(self)
        self.setCentralWidget(self.tables_list)
        self.db_manager = SimpleNamespace(loaded_tables={}, reload_table=Mock(return_value=(True, 'ok')))
        self._apply_column_renames_to_table = Mock()
        self.update_completer = Mock()
        self.show_table_preview = Mock()
        self.get_current_tab = Mock(return_value=object())
        self.reload_selected_table = Mock()
        self.show_refresh_failures = Mock()

    def add(self, name, source='source.csv', folder=None):
        self.db_manager.loaded_tables[name] = source
        return self.tables_list.add_table_item(name, source, needs_reload=True, folder_name=folder)


@pytest.fixture
def window(qapp, monkeypatch):
    window = RefreshWindow()
    monkeypatch.setattr(main, 'show_warning_notification', Mock())
    window.resize(400, 400)
    window.show()
    yield window
    window.close()
    window.deleteLater()


def test_batch_selection_and_updates(window):
    folder = window.tables_list.create_folder('Files')
    first = window.add('first')
    second = window.add('second', folder='Files')
    untouched = window.add('untouched')
    database = window.add('database_table', 'database')
    query = window.add('query_table', 'query_result')
    window.tables_list.setCurrentItem(second)
    for item in [folder, first, second, database, query]:
        item.setSelected(True)
    window.reload_selected_tables()
    assert set(c.args[0] for c in window.db_manager.reload_table.call_args_list) == {'first', 'second'}
    assert window.db_manager.reload_table.call_count == 2
    assert window._apply_column_renames_to_table.call_count == 2
    window.update_completer.assert_called_once_with()
    window.show_table_preview.assert_called_once_with(second)
    assert window.tables_list.tables_needing_reload == {'untouched', 'database_table', 'query_table'}
    assert window.statusBar().currentMessage() == 'Refresh complete: 2 refreshed, 2 skipped, 0 failed.'
    main.show_warning_notification.assert_not_called()
    assert untouched not in window.tables_list.selectedItems()


@pytest.mark.parametrize('failure', [(False, 'missing source'), RuntimeError('read failed')])
def test_failure_continues_and_duplicates_are_ignored(window, failure):
    first = window.add('first')
    second = window.add('second')
    window.tables_list.setCurrentItem(first)
    window.db_manager.reload_table.side_effect = [failure, (True, 'ok')]
    window.reload_selected_tables([first, first, second])
    assert window.db_manager.reload_table.call_args_list == [call('first'), call('second')]
    assert window.tables_list.tables_needing_reload == {'first'}
    window.update_completer.assert_called_once_with()
    window.show_table_preview.assert_not_called()
    window.show_refresh_failures.assert_called_once()
    assert 'first:' in window.show_refresh_failures.call_args.args[1][0]
    assert window.statusBar().currentMessage() == 'Refresh complete: 1 refreshed, 0 skipped, 1 failed.'


def test_empty_and_unsupported_selection(window):
    folder = window.tables_list.create_folder('Files')
    window.reload_selected_tables([folder])
    window.reload_selected_tables([window.add('db', 'database'), window.add('query', 'query_result')])
    window.db_manager.reload_table.assert_not_called()
    window.update_completer.assert_not_called()
    window.show_table_preview.assert_not_called()
    assert window.statusBar().currentMessage() == 'Refresh complete: 0 refreshed, 2 skipped, 0 failed.'


@pytest.mark.parametrize('kind', ['multiple', 'single', 'folder'])
def test_context_menu_routing(window, monkeypatch, kind):
    first = window.add('first')
    second = window.add('second')
    folder = window.tables_list.create_folder('Files')
    window.tables_list.clearSelection()
    target = folder if kind == 'folder' else first
    window.tables_list.setCurrentItem(target)
    if kind == 'multiple':
        second.setSelected(True)
    menus = []

    def choose(menu, position):
        labels = [a.text() for a in menu.actions()]
        menus.append(labels)
        label = {'multiple': 'Refresh Selected Tables', 'single': 'Reload Table', 'folder': 'New Subfolder'}[kind]
        assert label in labels
        if kind != 'multiple':
            assert 'Refresh Selected Tables' not in labels
        return next(a for a in menu.actions() if a.text() == label) if kind != 'folder' else None

    monkeypatch.setattr(QMenu, 'exec', choose)
    position = window.tables_list.visualItemRect(target).center()
    window.tables_list.customContextMenuRequested.emit(position)
    assert len(menus) == 1
    if kind == 'multiple':
        assert window.db_manager.reload_table.call_count == 2
    elif kind == 'single':
        window.reload_selected_table.assert_called_once_with('first')


@pytest.mark.parametrize('modifier', [Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier])
def test_mouse_multiselection_refresh(window, qapp, modifier):
    from PyQt6.QtTest import QTest

    first = window.add('first')
    folder = window.tables_list.create_folder('Files')
    second = window.add('second', folder='Files')
    qapp.processEvents()
    tree = window.tables_list
    QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton,
                     pos=tree.visualItemRect(first).center())
    QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, modifier,
                     pos=tree.visualItemRect(second).center())
    assert first in tree.selectedItems() and second in tree.selectedItems()
    window.reload_selected_tables()
    assert window.db_manager.reload_table.call_count == 2
    assert set(c.args[0] for c in window.db_manager.reload_table.call_args_list) == {'first', 'second'}


def test_refresh_all_includes_collapsed_nested_tables(window):
    from PyQt6.QtWidgets import QTreeWidgetItem

    first = window.add('first')
    folder = window.tables_list.create_folder('Files')
    nested = QTreeWidgetItem(folder)
    nested.setText(0, 'Nested')
    nested.setData(0, Qt.ItemDataRole.UserRole, 'folder')
    second = window.add('second')
    window.tables_list.takeTopLevelItem(window.tables_list.indexOfTopLevelItem(second))
    nested.addChild(second)
    window.add('db', 'database')
    window.add('query', 'query_result')
    window.tables_list.setCurrentItem(first)
    folder.setExpanded(False)
    nested.setExpanded(False)
    selection = window.tables_list.selectedItems()
    window.db_manager.reload_table.side_effect = [(False, 'missing source'), (True, 'ok')]
    header = window.create_tables_header()
    window.update_refresh_controls()
    window.refresh_all_button.click()
    assert window.db_manager.reload_table.call_args_list == [call('first'), call('second')]
    assert window.tables_list.selectedItems() == selection
    assert not folder.isExpanded() and not nested.isExpanded()
    window.update_completer.assert_called_once_with()
    window.show_table_preview.assert_not_called()
    assert window.statusBar().currentMessage() == 'Refresh complete: 1 refreshed, 2 skipped, 1 failed.'
    window.show_refresh_failures.assert_called_once()
    header.deleteLater()


def test_refresh_all_empty(window):
    window.reload_all_tables()
    window.db_manager.reload_table.assert_not_called()
    window.update_completer.assert_not_called()
    main.show_warning_notification.assert_not_called()


@pytest.mark.parametrize('oversized_button_hints', [False, True])
@pytest.mark.parametrize('wide_label', [False, True])
def test_header_layout_and_organization_actions(window, qapp, monkeypatch, oversized_button_hints, wide_label):
    from PyQt6.QtWidgets import QInputDialog, QLabel, QToolButton

    if wide_label:
        class WideLabel(QLabel):
            def minimumSizeHint(self):
                size = super().minimumSizeHint()
                size.setWidth(max(150, size.width()))
                return size

        monkeypatch.setattr(main, 'QLabel', WideLabel)

    if oversized_button_hints:
        class WideToolButton(QToolButton):
            def sizeHint(self):
                size = super().sizeHint()
                size.setWidth(max(120, size.width()))
                return size

            def minimumSizeHint(self):
                return self.sizeHint()

        monkeypatch.setattr(main, 'QToolButton', WideToolButton)

    folder = window.tables_list.create_folder('Files')
    current = window.add('first', folder='Files')
    window.tables_list.setCurrentItem(current)
    header = window.create_tables_header()
    # Match the font family inherited from the application in normal use.
    header.setStyleSheet("QWidget { font-family: 'Segoe UI', 'Arial', sans-serif; }")
    # Sidebar minimum width less its two 12px margins.
    header.setFixedWidth(196)
    header.show()
    qapp.processEvents()
    assert header.minimumSizeHint().width() <= 196
    label = header.findChild(QLabel, 'header_label')
    assert header.rect().contains(label.geometry())
    assert label.width() >= label.minimumSizeHint().width()
    for button in (window.refresh_all_button, window.tables_menu_button):
        assert button.accessibleName() and button.toolTip()
        assert header.rect().contains(button.geometry())
        assert button.width() >= button.fontMetrics().horizontalAdvance(button.text()) + 8
        assert not label.geometry().intersects(button.geometry())
    assert not window.refresh_all_button.geometry().intersects(window.tables_menu_button.geometry())
    actions = {action.text(): action for action in window.tables_menu_button.menu().actions()}
    actions['Collapse All'].trigger()
    assert not folder.isExpanded()
    actions['Expand All'].trigger()
    assert folder.isExpanded()
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args: ('New root', True))
    actions['New Folder'].trigger()
    tree = window.tables_list
    assert any(tree.topLevelItem(i).text(0) == 'New root' for i in range(tree.topLevelItemCount()))
    header.close()
    header.deleteLater()


def test_refresh_controls_follow_available_sources(window):
    header = window.create_tables_header()
    window.update_refresh_controls()
    assert not window.refresh_all_button.isEnabled()
    window.add('attached', 'database:external')
    window.update_refresh_controls()
    assert not window.refresh_all_button.isEnabled()
    window.add('file')
    window.update_refresh_controls()
    assert window.refresh_all_button.isEnabled()
    window._refresh_in_progress = True
    window.update_refresh_controls()
    assert not window.refresh_all_button.isEnabled()
    window._refresh_in_progress = False
    header.deleteLater()


def test_worker_keeps_event_loop_responsive(window):
    import threading
    from PyQt6.QtCore import QTimer

    window.add('file')
    released = threading.Event()
    worker_threads = []
    ticks = []

    def reload(name):
        worker_threads.append(threading.get_ident())
        assert released.wait(3), 'UI timer did not run during refresh'
        return True, 'ok'

    def tick():
        ticks.append(window._refresh_in_progress)
        released.set()

    window.db_manager.reload_table.side_effect = reload
    QTimer.singleShot(50, tick)
    window.reload_all_tables()
    assert ticks == [True]
    assert worker_threads[0] != threading.get_ident()
    window.show_refresh_failures.assert_not_called()


def test_real_csv_refresh_in_worker(window, tmp_path):
    import pandas as pd
    from sqlshell.db.database_manager import DatabaseManager

    manager = DatabaseManager()
    window.db_manager = manager
    source = tmp_path / 'data.csv'
    source.write_text('value\n2\n3\n')
    manager.register_dataframe(pd.DataFrame({'value': [1]}), 'data', str(source))
    item = window.tables_list.add_table_item('data', str(source))
    window.tables_list.setCurrentItem(item)
    try:
        window.reload_all_tables()
        assert manager.get_full_table('data')['value'].tolist() == [2, 3]
        window.show_table_preview.assert_called_once_with(item)
        window.show_refresh_failures.assert_not_called()
    finally:
        manager.close_connection()


def test_failure_dialog_exposes_all_details(window, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    failures = [f'table_{i}: missing source file' for i in range(30)]
    inspected = []

    def inspect(dialog):
        assert dialog.detailedText().splitlines() == failures
        assert dialog.text() == '30 failed'
        inspected.append(True)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, 'exec', inspect)
    main.SQLShell.show_refresh_failures(window, '30 failed', failures)
    assert inspected == [True]
