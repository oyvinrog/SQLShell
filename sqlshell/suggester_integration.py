"""
Integration module for context-aware SQL suggestions.

This module provides the glue code needed to connect the ContextSuggester
with the SQL editor component for seamless context-aware autocompletion.
Also integrates AI-powered suggestions when configured.
"""

from PyQt6.QtCore import QStringListModel, Qt, QMetaObject, Q_ARG
from PyQt6.QtWidgets import QCompleter
from typing import Dict, List, Any, Optional
import re

from sqlshell.context_suggester import ContextSuggester
from sqlshell.ai_autocomplete import get_ai_autocomplete_manager


class SuggestionManager:
    """
    Manages the integration between the ContextSuggester and the SQLEditor.
    
    This class acts as a bridge between the database schema information,
    query history tracking, and the editor's autocompletion functionality.
    Also integrates AI-powered suggestions when configured.
    """
    
    def __init__(self):
        """Initialize the suggestion manager."""
        self.suggester = ContextSuggester()
        self._completers = {}  # {editor_id: completer}
        self._editors = {}  # {editor_id: editor_instance}
        self._ai_manager = get_ai_autocomplete_manager()
        
        # Connect AI suggestion signal to handler with QueuedConnection for thread safety
        # This ensures signals from background threads are processed in the main thread
        self._ai_manager.suggestion_ready.connect(
            self._on_ai_suggestion_ready,
            Qt.ConnectionType.QueuedConnection
        )
        
        # Track which editor requested AI suggestion
        self._pending_ai_editor_id = None
    
    def register_editor(self, editor, editor_id=None):
        """
        Register an editor to receive context-aware suggestions.
        
        Args:
            editor: The SQLEditor instance to register
            editor_id: Optional identifier for the editor (defaults to object id)
        """
        print(f"[AI DEBUG] register_editor called with editor_id={editor_id}")
        if editor_id is None:
            editor_id = id(editor)
            
        # Create a completer for this editor if it doesn't have one
        if not hasattr(editor, 'completer') or not editor.completer:
            completer = QCompleter()
            completer.setWidget(editor)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.activated.connect(editor.insert_completion)
            editor.completer = completer
            
        self._completers[editor_id] = editor.completer
        self._editors[editor_id] = editor
        
        # Hook into editor's context detection methods if possible
        if hasattr(editor, 'get_context_at_cursor'):
            # Save the original method
            if not hasattr(editor, '_original_get_context_at_cursor'):
                editor._original_get_context_at_cursor = editor.get_context_at_cursor
                
            # Replace with our enhanced version
            def enhanced_get_context(editor_ref=editor, suggestion_mgr=self):
                # Get the original context first
                original_context = editor_ref._original_get_context_at_cursor()
                
                # Get our enhanced context
                tc = editor_ref.textCursor()
                position = tc.position()
                doc = editor_ref.document()
                
                # Get text before cursor - the error was in this section
                # Using a simpler approach that doesn't rely on QTextDocument.find()
                text_before_cursor = editor_ref.toPlainText()[:position]
                current_word = editor_ref.get_word_under_cursor()
                
                enhanced_context = suggestion_mgr.suggester.analyze_context(
                    text_before_cursor,
                    current_word
                )
                
                # Merge the contexts (our enhanced context takes precedence)
                merged_context = {**original_context, **enhanced_context}
                return merged_context
                
            editor.get_context_at_cursor = enhanced_get_context
            
        # Hook into editor's complete method if possible
        print(f"[AI DEBUG] Checking if editor has 'complete': {hasattr(editor, 'complete')}")
        if hasattr(editor, 'complete'):
            # Save the original method
            print(f"[AI DEBUG] Has _original_complete already? {hasattr(editor, '_original_complete')}")
            if not hasattr(editor, '_original_complete'):
                editor._original_complete = editor.complete
                print(f"[AI DEBUG] Saved _original_complete: {editor._original_complete}")
                
            # Replace with our enhanced version for ghost text
            def enhanced_complete(editor_ref=editor, suggestion_mgr=self):
                print(f"[AI DEBUG] enhanced_complete called!")
                tc = editor_ref.textCursor()
                position = tc.position()
                text_before_cursor = editor_ref.toPlainText()[:position]
                current_word = editor_ref.get_word_under_cursor()
                print(f"[AI DEBUG] position={position}, text_len={len(text_before_cursor)}, word='{current_word}'")
                
                # Check if Ctrl key is being held down
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtCore import Qt
                
                # Don't show completions if Ctrl key is pressed (could be in preparation for Ctrl+Enter)
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    # Clear any ghost text if Ctrl is held down
                    if hasattr(editor_ref, 'clear_ghost_text'):
                        editor_ref.clear_ghost_text()
                    return
                
                # Special handling for function argument completions
                # This helps with context like SELECT AVG(...) FROM table
                in_function = False
                open_parens = text_before_cursor.count('(')
                close_parens = text_before_cursor.count(')')
                
                if open_parens > close_parens:
                    in_function = True
                    # Get further context for better suggestions inside function arguments
                    context = suggestion_mgr.suggester.analyze_context(text_before_cursor, current_word)
                    if 'tables_in_from' not in context or not context['tables_in_from']:
                        # If tables not yet detected, try to look ahead for FROM clause
                        full_text = editor_ref.toPlainText()
                        after_cursor = full_text[position:]
                        # Look for FROM clause after current position
                        from_match = re.search(r'FROM\s+([a-zA-Z0-9_]+)', after_cursor, re.IGNORECASE)
                        if from_match:
                            table_name = from_match.group(1)
                            # Add this table to the context for better suggestions
                            context['tables_in_from'] = [table_name]
                            # Update the context in suggester
                            suggestion_mgr.suggester._context_cache[f"{text_before_cursor}:{current_word}"] = context
                
                # Get context-aware suggestions from the local suggester
                suggestions = suggestion_mgr.get_suggestions(text_before_cursor, current_word)
                
                # Check if AI autocomplete is available and should be used
                ai_manager = suggestion_mgr._ai_manager
                use_ai = (
                    ai_manager.is_available and 
                    len(text_before_cursor.strip()) >= 3  # Only use AI for non-trivial context
                )
                
                if suggestions and hasattr(editor_ref, 'show_ghost_text'):
                    # Find the best suggestion using the same logic as the editor's complete method
                    prefix = editor_ref.text_under_cursor()
                    
                    # Sort by relevance - prioritize exact prefix matches and shorter suggestions
                    def relevance_score(item):
                        item_lower = item.lower()
                        prefix_lower = prefix.lower()
                        
                        # Perfect case match gets highest priority
                        if item.startswith(prefix):
                            return (0, len(item))
                        # Case-insensitive prefix match
                        elif item_lower.startswith(prefix_lower):
                            return (1, len(item))
                        # Contains the prefix somewhere
                        elif prefix_lower in item_lower:
                            return (2, len(item))
                        else:
                            return (3, len(item))
                    
                    suggestions.sort(key=relevance_score)
                    best_suggestion = suggestions[0]
                    
                    # Show ghost text for the best suggestion
                    editor_ref.show_ghost_text(best_suggestion, position)
                    
                    # Also request AI suggestion in background (may override if better)
                    if use_ai:
                        suggestion_mgr._pending_ai_editor_id = id(editor_ref)
                        ai_manager.request_suggestion(
                            text_before_cursor, 
                            current_word, 
                            position
                        )
                elif use_ai:
                    # No local suggestions, try AI
                    suggestion_mgr._pending_ai_editor_id = id(editor_ref)
                    ai_manager.request_suggestion(
                        text_before_cursor, 
                        current_word, 
                        position
                    )
                else:
                    # Clear ghost text if no suggestions
                    if hasattr(editor_ref, 'clear_ghost_text'):
                        editor_ref.clear_ghost_text()
                    
                    # Fall back to original completion if no context-aware suggestions
                    if hasattr(editor_ref, '_original_complete'):
                        editor_ref._original_complete()
                    
            editor.complete = enhanced_complete
            print(f"[AI DEBUG] Replaced complete method. Now: {editor.complete}")
    
    def unregister_editor(self, editor_id):
        """
        Unregister an editor from receiving context-aware suggestions.
        
        Args:
            editor_id: The identifier of the editor to unregister
        """
        if editor_id in self._editors:
            editor = self._editors[editor_id]
            
            # Restore original methods if we replaced them
            if hasattr(editor, '_original_get_context_at_cursor'):
                editor.get_context_at_cursor = editor._original_get_context_at_cursor
                delattr(editor, '_original_get_context_at_cursor')
                
            if hasattr(editor, '_original_complete'):
                editor.complete = editor._original_complete
                delattr(editor, '_original_complete')
            
            # Remove from tracked collections
            del self._editors[editor_id]
            
        if editor_id in self._completers:
            del self._completers[editor_id]
    
    def _on_ai_suggestion_ready(self, suggestion: str, cursor_position: int):
        """Handle AI suggestion ready signal."""
        print(f"[AI] Signal received: '{suggestion[:30]}...' for position {cursor_position}")
        
        if not suggestion or not self._pending_ai_editor_id:
            print(f"[AI] Skipping: no suggestion or no pending editor (editor_id: {self._pending_ai_editor_id})")
            return
        
        # Find the editor that requested the suggestion
        # The pending_ai_editor_id is now stored as the actual editor object id
        editor = None
        for editor_key, stored_editor in self._editors.items():
            if id(stored_editor) == self._pending_ai_editor_id:
                editor = stored_editor
                break
        
        if not editor:
            print(f"[AI] Editor not found for id: {self._pending_ai_editor_id}")
            print(f"[AI] Available editors: {[(k, id(v)) for k, v in self._editors.items()]}")
            return
        
        # Verify cursor is still at the expected position
        current_position = editor.textCursor().position()
        if abs(current_position - cursor_position) > 5:  # Allow small tolerance
            print(f"[AI] Cursor moved too much: expected ~{cursor_position}, got {current_position}")
            return  # Cursor moved too much, discard suggestion
        
        # Show the AI suggestion as ghost text
        if hasattr(editor, 'show_ghost_text'):
            print(f"[AI] Showing ghost text: '{suggestion[:30]}...'")
            # Mark this as an AI suggestion (could be used to show different styling)
            editor._is_ai_suggestion = True
            editor.show_ghost_text(suggestion, current_position)
        else:
            print(f"[AI] Editor doesn't have show_ghost_text method")
    
    def update_schema(self, tables, table_columns, column_types=None):
        """
        Update schema information for all registered editors.
        
        Args:
            tables: Set of table names
            table_columns: Dictionary mapping table names to column lists
            column_types: Optional dictionary of column data types
        """
        # Update the context suggester with new schema information
        self.suggester.update_schema(tables, table_columns, column_types)
        
        # Also update AI manager with schema context
        self._ai_manager.update_schema_context(list(tables), table_columns)
    
    def record_query(self, query_text):
        """
        Record a query to improve suggestion relevance.
        
        Args:
            query_text: The SQL query to record
        """
        self.suggester.record_query(query_text)
    
    def get_suggestions(self, text_before_cursor, current_word=""):
        """
        Get context-aware suggestions for the given text context.
        
        Args:
            text_before_cursor: Text from start of document to cursor position
            current_word: The current word being typed (possibly empty)
            
        Returns:
            List of suggestion strings relevant to the current context
        """
        return self.suggester.get_suggestions(text_before_cursor, current_word)
    
    def update_all_completers(self):
        """Update all registered completers with current schema and usage data."""
        for editor_id, editor in self._editors.items():
            # Force a completion update next time complete() is called
            if hasattr(editor, '_context_cache'):
                editor._context_cache = {}


# Create a singleton instance to be used application-wide
suggestion_manager = SuggestionManager()


def get_suggestion_manager():
    """Get the global suggestion manager instance."""
    return suggestion_manager 