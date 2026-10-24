"""Regression tests for results-table clipboard actions."""

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMenu, QTableWidgetItem, QTableWidgetSelectionRange

from sqlshell.widgets import CopyableTableWidget


pytestmark = pytest.mark.gui


@pytest.fixture
def table(qapp):
    widget = CopyableTableWidget()
    widget.setColumnCount(2)
    widget.setRowCount(2)
    widget.setHorizontalHeaderLabels(["name", "city"])
    for row, values in enumerate([("Alice", "Oslo"), ("Bob", "Bergen")]):
        for col, value in enumerate(values):
            widget.setItem(row, col, QTableWidgetItem(value))
    qapp.clipboard().clear()
    yield widget
    widget.close()
    widget.deleteLater()


@pytest.mark.parametrize("include_headers", [False, True])
@pytest.mark.parametrize(
    "bounds, values, headers",
    [
        ((0, 0, 0, 0), "Alice", "name"),
        ((1, 0, 1, 0), "Bob", "name"),
        ((0, 0, 1, 0), "Alice\nBob", "name"),
        ((0, 0, 1, 1), "Alice\tOslo\nBob\tBergen", "name\tcity"),
    ],
)
def test_selection_headers(table, qapp, bounds, values, headers, include_headers):
    table.setRangeSelected(QTableWidgetSelectionRange(*bounds), True)
    table.copy_selection_to_clipboard(include_headers=include_headers)
    expected = f"{headers}\n{values}" if include_headers else values
    assert qapp.clipboard().text() == expected


def test_single_cell_result(table, qapp):
    table.setRowCount(1)
    table.setColumnCount(1)
    table.setCurrentCell(0, 0)
    table.copy_selection_to_clipboard()
    assert qapp.clipboard().text() == "Alice"


def test_ctrl_c_omits_headers(table, qapp):
    table.setCurrentCell(0, 0)
    QTest.keyClick(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    assert qapp.clipboard().text() == "Alice"


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Copy Selection (Ctrl+C)", "Alice"),
        ("Copy Selection + Header", "name\nAlice"),
    ],
)
def test_context_menu_actions(table, qapp, monkeypatch, label, expected):
    table.setCurrentCell(0, 0)

    def trigger_action(menu, position):
        action = next(action for action in menu.actions() if action.text() == label)
        assert action.shortcut().isEmpty()
        action.trigger()
        return action

    monkeypatch.setattr(QMenu, "exec", trigger_action)
    table.show_context_menu(QPoint())
    assert qapp.clipboard().text() == expected


def test_no_selection_menu(table, monkeypatch):
    def inspect_menu(menu, position):
        labels = [action.text() for action in menu.actions()]
        assert "Copy Selection (Ctrl+C)" not in labels
        assert "Copy Selection + Header" not in labels
        assert "Copy All Data" in labels

    monkeypatch.setattr(QMenu, "exec", inspect_menu)
    table.show_context_menu(QPoint())


@pytest.mark.parametrize("operation", ["all", "selection", "selection_with_headers"])
def test_copy_all_and_no_selection_fallback(table, qapp, operation):
    if operation == "all":
        table.copy_all_to_clipboard()
    else:
        table.copy_selection_to_clipboard(
            include_headers=operation == "selection_with_headers"
        )
    assert qapp.clipboard().text() == "name\tcity\nAlice\tOslo\nBob\tBergen"
