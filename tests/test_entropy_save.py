"""Column importance export through the application's Save as Table flow."""

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from PyQt6.QtWidgets import QPushButton

from sqlshell import __main__ as main
from sqlshell.utils.profile_entropy import EntropyVisualization, profile, visualize_profile


pytestmark = pytest.mark.gui


@pytest.fixture
def shell(db_manager, monkeypatch):
    host = SimpleNamespace(
        db_manager=db_manager,
        tables_list=Mock(tables_needing_reload=set()),
        statusBar=Mock(return_value=Mock()),
        update_completer=Mock(),
    )
    host.save_results_as_table = lambda df: main.SQLShell.save_results_as_table(host, df)
    monkeypatch.setattr(main.QMessageBox, "information", Mock())
    monkeypatch.setattr(main, "show_error_notification", Mock())
    return host


@pytest.mark.parametrize("entry_point", ["table", "query"])
def test_analysis_save_round_trip(qapp, shell, tmp_path, monkeypatch, entry_point):
    source = pd.DataFrame({"category": ["a", "a", "b"], "constant": [1, 1, 1]})
    expected = profile(source).reset_index(drop=True)
    path = tmp_path / "importance.parquet"
    monkeypatch.setattr(main.QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    # An existing table must survive the save under a colliding name.
    shell.db_manager.register_dataframe(source, "importance")
    if entry_point == "table":
        main.SQLShell.analyze_table_entropy(shell, "importance")
    else:
        shell.get_current_tab = lambda: SimpleNamespace(current_df=source)
        main.SQLShell.analyze_current_data_entropy(shell)
    window = shell._entropy_window
    try:
        window.save_button.click()
        saved = shell.db_manager.execute_query('SELECT * FROM "importance_1"')
        pd.testing.assert_frame_equal(saved, expected)
        pd.testing.assert_frame_equal(pd.read_parquet(path), expected)
        pd.testing.assert_frame_equal(
            shell.db_manager.execute_query('SELECT * FROM "importance"'), source
        )
        shell.tables_list.add_table_item.assert_called_once_with("importance_1", path.name)
        shell.update_completer.assert_called_once()
        main.show_error_notification.assert_not_called()
    finally:
        window.close()


@pytest.mark.parametrize("failure", [False, True])
def test_cancel_or_failed_save_creates_no_table(qapp, shell, tmp_path, monkeypatch, failure):
    path = tmp_path / "importance.parquet"
    monkeypatch.setattr(
        main.QFileDialog, "getSaveFileName",
        lambda *args: (str(path) if failure else "", ""),
    )
    if failure:
        monkeypatch.setattr(pd.DataFrame, "to_parquet", Mock(side_effect=OSError("write failed")))
    window = visualize_profile(pd.DataFrame({"value": [1, 2, 3]}), shell.save_results_as_table)
    try:
        window.save_button.click()
        assert not shell.db_manager.loaded_tables
        assert not path.exists()
        shell.tables_list.add_table_item.assert_not_called()
        if failure:
            main.show_error_notification.assert_called_once_with("Failed to save as table: write failed")
        else:
            main.show_error_notification.assert_not_called()
    finally:
        window.close()


def test_empty_and_standalone_analysis(qapp):
    callback = Mock()
    empty = EntropyVisualization(profile(pd.DataFrame()), save_callback=callback)
    standalone = visualize_profile(pd.DataFrame({"value": [1, 2, 3]}))
    try:
        assert not empty.save_button.isEnabled()
        empty.save_button.click()
        callback.assert_not_called()
        assert not standalone.findChildren(QPushButton)
    finally:
        empty.close()
        standalone.close()
