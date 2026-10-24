"""Folder sources discover lazily and share the existing on-demand loading path."""
import json
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMenu, QMessageBox

from sqlshell.db.database_manager import DatabaseManager
from sqlshell.folder_sources import discover_files
from sqlshell.folder_source_ui import FolderSourceWindowMixin, source_item_info, source_icon
from sqlshell.refresh_dialog import RefreshWorker
from sqlshell.project_manager import ProjectManager
from sqlshell.__main__ import SQLShell
from tests.test_table_refresh import RefreshWindow
from tests.test_project_manager import MockWindow


@pytest.fixture
def manager():
    manager = DatabaseManager()
    yield manager
    manager.close_connection()


def csv(path, value=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'value\n{value}\n')
    return path


def test_scan_formats_delta_symlinks_and_sorting(tmp_path):
    for name in ['z.XLSX', 'a.csv', 'a.xls', 'b.TXT', 'c.PARQUET',
                 'nested/table.csv', 'ignore.sqlite', 'ignore.duckdb', 'ignore.pdf']:
        csv(tmp_path / name)
    (tmp_path / 'delta' / '_delta_log').mkdir(parents=True)
    csv(tmp_path / 'delta' / 'internal.parquet')
    (tmp_path / 'loop').symlink_to(tmp_path, target_is_directory=True)
    paths, errors = discover_files(tmp_path)
    assert not errors
    assert paths == ['a.csv', 'a.xls', 'b.TXT', 'c.PARQUET', 'delta', 'nested/table.csv', 'z.XLSX']


def test_discovery_is_lazy_names_stable_and_overlap_independent(manager, tmp_path, monkeypatch):
    csv(tmp_path / 'a.csv')
    csv(tmp_path / 'nested' / 'a.CSV', 2)
    monkeypatch.setattr(manager, 'load_file', Mock(side_effect=AssertionError('must not read data')))
    key = manager.add_folder_source(tmp_path)
    assert manager.add_folder_source(tmp_path / '.') == key
    added, errors = manager.discover_folder_source(key)
    assert added == ['a', 'a_1'] and not errors
    assert manager.conn.execute('SHOW TABLES').fetchall() == []
    assert manager.discover_folder_source(key) == ([], [])
    overlap = manager.add_folder_source(tmp_path / 'nested')
    assert manager.discover_folder_source(overlap)[0] == ['a_2']
    manager.load_file.assert_not_called()


def test_on_demand_and_failed_refresh_preserves_data(manager, tmp_path):
    path = csv(tmp_path / 'data.CSV', 7)
    key = manager.add_folder_source(tmp_path)
    manager.discover_folder_source(key)
    assert manager.reload_table('data')[0]
    assert manager.get_full_table('data')['value'].tolist() == [7]
    path.write_bytes(b'')
    assert not manager.reload_table('data')[0]
    assert manager.get_full_table('data')['value'].tolist() == [7]
    path.unlink()
    assert not manager.reload_table('data')[0]
    assert manager.folder_sources[key]['members'] == {'data.CSV': 'data'}
    csv(path, 9)
    assert manager.reload_table('data')[0]
    assert manager.get_full_table('data')['value'].tolist() == [9]


def test_exclusion_restore_and_rename(manager, tmp_path):
    csv(tmp_path / 'a.csv')
    key = manager.add_folder_source(tmp_path)
    manager.discover_folder_source(key)
    assert manager.reload_table('a')[0]
    assert manager.rename_table('a', 'renamed')
    assert manager.folder_sources[key]['members']['a.csv'] == 'renamed'
    assert manager.remove_table('renamed')
    assert manager.folder_sources[key]['excluded'] == ['a.csv']
    assert manager.discover_folder_source(key)[0] == []
    manager.folder_sources[key]['excluded'].clear()
    assert manager.discover_folder_source(key)[0] == ['a']
    assert manager.conn.execute('SHOW TABLES').fetchall() == []


def test_worker_deduplicates_selected_tables_and_folder_subtrees(manager, tmp_path):
    csv(tmp_path / 'a.csv')
    csv(tmp_path / 'nested' / 'b.csv')
    key = manager.add_folder_source(tmp_path)
    manager.discover_folder_source(key)
    csv(tmp_path / 'nested' / 'new.csv')
    worker = RefreshWorker(manager, ['b'], folders=[(key, 'nested')])
    worker.run()
    assert [name for name, ok, _ in worker.results if ok] == ['b', 'new']
    assert worker.added == ['new']
    assert manager.conn.execute('SHOW TABLES').fetchall() == [('b',), ('new',)]


class FolderWindow(FolderSourceWindowMixin, RefreshWindow):
    pass


@pytest.fixture
def window(qapp, manager):
    window = FolderWindow()
    window.db_manager = manager
    yield window
    window.deleteLater()


def test_ui_add_is_lazy_selection_refresh_and_new_files(window, tmp_path):
    csv(tmp_path / 'a.csv')
    csv(tmp_path / 'nested' / 'b.csv')
    window.add_folder_source(str(tmp_path))
    tree = window.tables_list
    assert tree.tables_needing_reload == {'a', 'b'}
    assert window.db_manager.conn.execute('SHOW TABLES').fetchall() == []
    root = tree.topLevelItem(0)
    assert source_item_info(root) == (str(tmp_path), '')
    assert tree.find_table_item('b').parent().text(0) == 'nested'
    assert not source_icon().isNull()
    assert not root.flags() & Qt.ItemFlag.ItemIsDropEnabled
    window.add_folder_source(str(tmp_path))
    assert tree.topLevelItemCount() == 1
    # Selected refresh must not discover or read unselected files.
    csv(tmp_path / 'new.csv')
    window.reload_selected_tables([tree.find_table_item('b')])
    assert tree.tables_needing_reload == {'a'}
    assert 'new' not in window.db_manager.loaded_tables
    window.reload_selected_tables([root, tree.find_table_item('b')])
    assert tree.tables_needing_reload == set()
    assert set(window.db_manager.loaded_tables) == {'a', 'b', 'new'}
    window.show_refresh_failures.assert_not_called()


def test_empty_folder_can_refresh_and_missing_members_warn(window, tmp_path):
    window.add_folder_source(str(tmp_path))
    header = window.create_tables_header()
    window.update_refresh_controls()
    assert window.refresh_all_button.isEnabled()
    path = csv(tmp_path / 'new.csv')
    window.reload_all_tables()
    path.unlink()
    window.reload_all_tables()
    item = window.tables_list.find_table_item('new')
    assert 'stale' in item.toolTip(0)
    assert 'new' in window.tables_list.tables_needing_reload
    assert window.db_manager.get_full_table('new')['value'].tolist() == [1]
    csv(path, 2)
    window.reload_all_tables()
    assert item.toolTip(0) == str(path)
    header.deleteLater()


def test_source_menu_remove_and_movement_guards(window, tmp_path, monkeypatch):
    path = csv(tmp_path / 'a.csv')
    window.add_folder_source(str(tmp_path))
    tree = window.tables_list
    root, item = tree.topLevelItem(0), tree.find_table_item('a')
    ordinary = tree.create_folder('Ordinary')
    tree.move_item_to_folder(item, ordinary)
    assert item.parent() is root
    other = tree.add_table_item('other', 'query_result')
    tree.move_item_to_folder(other, root)
    assert other.parent() is None
    labels = []
    def choose(menu, position):
        labels.extend(a.text() for a in menu.actions())
        return None
    monkeypatch.setattr(QMenu, 'exec', choose)
    window.folder_source_context_menu(root, tree.visualItemRect(root).center())
    assert labels == ['Refresh Folder', 'Restore Excluded Files…', 'Remove Folder Source']
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
    window.remove_folder_source(str(tmp_path))
    assert not window.db_manager.folder_sources
    assert 'a' not in window.db_manager.loaded_tables
    assert path.exists()


class ProjectWindow(FolderSourceWindowMixin, MockWindow):
    update_refresh_controls = SQLShell.update_refresh_controls
    show_refresh_failures = Mock()


def test_project_roundtrip_is_lazy_with_exclusions_and_missing_files(qapp, tmp_path, monkeypatch):
    path = csv(tmp_path / 'source' / 'nested' / 'a.csv')
    csv(tmp_path / 'source' / 'excluded.csv')
    window = ProjectWindow()
    window.add_tab()
    try:
        window.add_folder_source(str(path.parent.parent))
        key = str(path.parent.parent)
        window.db_manager.remove_table('excluded')
        excluded = window.tables_list.find_table_item('excluded')
        excluded.parent().removeChild(excluded)
        window.tables_list.topLevelItem(0).setExpanded(False)
        project = ProjectManager(window)
        saved = tmp_path / 'project.sqls'
        project.save_project_to_file(str(saved))
        data = json.loads(saved.read_text())
        assert data['folder_sources'][key]['excluded'] == ['excluded.csv']
        path.unlink()
        # Opening a project must not invoke either scanning or data readers.
        monkeypatch.setattr(window.db_manager, 'load_file', Mock(side_effect=AssertionError('read')))
        monkeypatch.setattr(window.db_manager, 'discover_folder_source', Mock(side_effect=AssertionError('scan')))
        project.open_project(str(saved))
        assert window.db_manager.folder_sources == data['folder_sources']
        assert window.tables_list.tables_needing_reload == {'a'}
        root = window.tables_list.topLevelItem(0)
        assert not root.isExpanded()
        assert source_item_info(root) == (key, '')
        assert window.tables_list.find_table_item('a').parent().text(0) == 'nested'
        window.db_manager.load_file.assert_not_called()
        window.db_manager.discover_folder_source.assert_not_called()
    finally:
        window.db_manager.close_connection()
        window.deleteLater()


def test_discovery_worker_keeps_ui_responsive(window, tmp_path, monkeypatch):
    import threading
    csv(tmp_path / 'a.csv')
    released = threading.Event()
    original = window.db_manager.discover_folder_source
    threads = []
    def scan(*args):
        threads.append(threading.get_ident())
        assert released.wait(3), 'GUI event loop blocked during discovery'
        return original(*args)
    monkeypatch.setattr(window.db_manager, 'discover_folder_source', scan)
    QTimer.singleShot(30, released.set)
    window.add_folder_source(str(tmp_path))
    assert threads[0] != threading.get_ident()
    assert window.db_manager.conn.execute('SHOW TABLES').fetchall() == []


def test_restore_exclusion_checklist_is_lazy(window, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QDialog, QListWidget
    csv(tmp_path / 'a.csv')
    csv(tmp_path / 'b.csv')
    window.add_folder_source(str(tmp_path))
    for name in ['a', 'b']:
        window.db_manager.remove_table(name)
        item = window.tables_list.find_table_item(name)
        item.parent().removeChild(item)
    def choose(dialog):
        dialog.findChild(QListWidget).item(0).setCheckState(Qt.CheckState.Checked)
        return QDialog.DialogCode.Accepted
    # Only replace the checklist's exec, leaving the background progress dialog intact.
    original = QDialog.exec
    monkeypatch.setattr(QDialog, 'exec', lambda dialog:
        choose(dialog) if dialog.windowTitle() == 'Restore Excluded Files' else original(dialog))
    window.restore_excluded_files(str(tmp_path))
    assert window.db_manager.folder_sources[str(tmp_path)]['excluded'] == ['b.csv']
    assert set(window.db_manager.loaded_tables) == {'a'}
    assert window.db_manager.conn.execute('SHOW TABLES').fetchall() == []


def test_excel_parquet_and_delta_load_only_when_requested(manager, tmp_path):
    frame = pd.DataFrame({'value': [42]})
    with pd.ExcelWriter(tmp_path / 'book.XLSX', engine='openpyxl') as writer:
        frame.to_excel(writer, sheet_name='First', index=False)
        pd.DataFrame({'ignored': [9]}).to_excel(writer, sheet_name='Second', index=False)
    frame.to_parquet(tmp_path / 'data.PARQUET', engine='fastparquet')
    from deltalake import write_deltalake
    import pyarrow as pa
    write_deltalake(str(tmp_path / 'delta'), pa.Table.from_pandas(frame))
    key = manager.add_folder_source(tmp_path)
    manager.discover_folder_source(key)
    assert set(manager.loaded_tables) == {'book', 'data', 'delta'}
    assert manager.conn.execute('SHOW TABLES').fetchall() == []
    for name in ['book', 'data', 'delta']:
        assert manager.reload_table(name)[0]
        assert manager.get_full_table(name).to_dict('list') == {'value': [42]}


def test_real_query_and_preview_load_only_referenced_tables(qapp, tmp_path, monkeypatch):
    import sqlshell.notification_manager as notifications
    monkeypatch.setattr(notifications, '_notification_manager', None)
    # Avoid reading or writing the developer's recent-project preferences.
    monkeypatch.setattr(SQLShell, 'load_recent_projects', lambda self: None)
    monkeypatch.setattr(SQLShell, 'load_recent_files', lambda self: None)
    monkeypatch.setattr(SQLShell, 'load_most_recent_project', lambda self: None)
    csv(tmp_path / 'queried.csv', 3)
    csv(tmp_path / 'previewed.csv', 4)
    csv(tmp_path / 'unused.csv', 5)
    window = SQLShell()
    try:
        window.add_folder_source(str(tmp_path))
        assert window.db_manager.conn.execute('SHOW TABLES').fetchall() == []
        window.execute_specific_query('SELECT * FROM queried')
        assert window.db_manager.conn.execute('SHOW TABLES').fetchall() == [('queried',)]
        window.show_table_preview(window.tables_list.find_table_item('previewed'))
        assert window.tables_list.tables_needing_reload == {'unused'}
        assert window.db_manager.conn.execute('SHOW TABLES').fetchall() == [('previewed',), ('queried',)]
    finally:
        window.db_manager.close_connection()
        window.deleteLater()
