"""Filesystem discovery and persistent, lazy folder-source registrations.

No UI or file readers belong here: discovery must never materialize table data.
"""
import os
from pathlib import Path

DATA_SUFFIXES = {'.xlsx', '.xls', '.csv', '.txt', '.parquet', '.delta'}


def canonical_folder(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def discover_files(root, relative=''):
    """Return sorted relative paths and scan errors; never descend into Delta."""
    root = Path(root)
    start = root / relative
    found, errors = [], []

    def visit(directory):
        try:
            if (directory / '_delta_log').is_dir():
                found.append(directory.relative_to(root).as_posix())
                return
            with os.scandir(directory) as entries:
                entries = sorted(entries, key=lambda entry: entry.name)
            for entry in entries:
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    visit(path)
                elif entry.is_file() and path.suffix.lower() in DATA_SUFFIXES:
                    found.append(path.relative_to(root).as_posix())
        except OSError as exc:
            errors.append((str(directory), str(exc)))

    visit(start)
    return sorted(found), errors


def in_subtree(relative, subtree):
    return not subtree or relative == subtree or relative.startswith(subtree.rstrip('/') + '/')


class FolderSourcesMixin:
    """Database-manager operations; callers serialize access to the connection."""

    def add_folder_source(self, path):
        key = canonical_folder(path)
        if key not in self.folder_sources:
            if not Path(key).is_dir():
                raise ValueError(f'Folder does not exist: {path}')
            self.folder_sources[key] = {'path': key, 'members': {}, 'excluded': []}
        return key

    def discover_folder_source(self, key, subtree=''):
        source = self.folder_sources[key]
        paths, errors = discover_files(source['path'], subtree)
        added = []
        for relative in paths:
            if relative in source['excluded'] or relative in source['members']:
                continue
            path = Path(source['path']) / relative
            base = path.name if path.is_dir() else path.stem
            original = self.sanitize_table_name(base)
            name, suffix = original, 1
            while name in self.loaded_tables:
                name = f'{original}_{suffix}'
                suffix += 1
            source['members'][relative] = name
            self.loaded_tables[name] = str(path)
            self.table_columns[name] = []
            added.append(name)
        return added, errors

    def folder_member(self, name):
        for key, source in self.folder_sources.items():
            for relative, member in source['members'].items():
                if member == name:
                    return key, relative
        return None

    def exclude_folder_member(self, name):
        member = self.folder_member(name)
        if member:
            key, relative = member
            source = self.folder_sources[key]
            del source['members'][relative]
            if relative not in source['excluded']:
                source['excluded'].append(relative)
                source['excluded'].sort()
