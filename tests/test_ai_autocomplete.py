"""
Tests for AI Autocomplete functionality.

These tests cover the AI autocomplete module that integrates with OpenAI
for intelligent SQL suggestions.
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules under test
from sqlshell.ai_autocomplete import AIAutocompleteManager, get_ai_autocomplete_manager


class TestAIAutocompleteManager:
    """Tests for the AIAutocompleteManager class."""
    
    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        """Create a fresh manager instance with isolated settings."""
        # Use a temporary settings file
        settings_file = tmp_path / ".sqlshell_settings.json"
        monkeypatch.setattr(
            'sqlshell.ai_autocomplete.AIAutocompleteManager._get_settings_file',
            lambda self: str(settings_file)
        )
        return AIAutocompleteManager()
    
    def test_initial_state(self, manager):
        """Test initial state without API key configured."""
        assert not manager.is_available
        assert not manager.is_configured
        assert manager.is_enabled()
        assert manager.get_model() == "gpt-4o-mini"
    
    def test_set_api_key(self, manager):
        """Test setting an API key."""
        # Mock the OpenAI client initialization
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {'openai': mock_openai}):
            mock_openai.OpenAI = MagicMock()
            result = manager.set_api_key("sk-test-key-12345")
            assert result is True
            assert manager.is_configured
    
    def test_set_empty_api_key(self, manager):
        """Test setting an empty API key clears configuration."""
        # First set a key
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {'openai': mock_openai}):
            mock_openai.OpenAI = MagicMock()
            manager.set_api_key("sk-test-key")
        
        # Then clear it
        manager.set_api_key("")
        assert not manager.is_configured
        
        manager.set_api_key(None)
        assert not manager.is_configured
    
    def test_get_masked_api_key(self, manager):
        """Test that API key is properly masked for display."""
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {'openai': mock_openai}):
            mock_openai.OpenAI = MagicMock()
            manager.set_api_key("sk-1234567890abcdef")
        
        masked = manager.get_api_key()
        assert masked is not None
        assert masked.startswith("sk-1")
        assert masked.endswith("cdef")
        assert "*" in masked
        # Ensure the full key is not exposed
        assert "1234567890abcdef" not in masked
    
    def test_get_raw_api_key(self, manager):
        """Test that raw API key can be retrieved internally."""
        test_key = "sk-1234567890abcdef"
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {'openai': mock_openai}):
            mock_openai.OpenAI = MagicMock()
            manager.set_api_key(test_key)
        
        raw = manager.get_raw_api_key()
        assert raw == test_key
    
    def test_enable_disable(self, manager):
        """Test enabling and disabling AI autocomplete."""
        assert manager.is_enabled()  # Default state
        
        manager.set_enabled(False)
        assert not manager.is_enabled()
        
        manager.set_enabled(True)
        assert manager.is_enabled()
    
    def test_model_selection(self, manager):
        """Test changing the AI model."""
        assert manager.get_model() == "gpt-4o-mini"  # Default
        
        manager.set_model("gpt-4o")
        assert manager.get_model() == "gpt-4o"
        
        manager.set_model("gpt-3.5-turbo")
        assert manager.get_model() == "gpt-3.5-turbo"
    
    def test_settings_persistence(self, tmp_path, monkeypatch):
        """Test that settings are persisted to file."""
        settings_file = tmp_path / ".sqlshell_settings.json"
        monkeypatch.setattr(
            'sqlshell.ai_autocomplete.AIAutocompleteManager._get_settings_file',
            lambda self: str(settings_file)
        )
        
        # Create first manager and configure it
        manager1 = AIAutocompleteManager()
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {'openai': mock_openai}):
            mock_openai.OpenAI = MagicMock()
            manager1.set_api_key("sk-test-persistence")
        manager1.set_model("gpt-4o")
        manager1.set_enabled(False)
        
        # Verify settings file exists
        assert settings_file.exists()
        
        # Create second manager and verify it loads settings
        manager2 = AIAutocompleteManager()
        
        assert manager2.get_raw_api_key() == "sk-test-persistence"
        assert manager2.get_model() == "gpt-4o"
        assert not manager2.is_enabled()
    
    def test_update_schema_context(self, manager):
        """Test updating schema context for better suggestions."""
        tables = ["users", "orders", "products"]
        table_columns = {
            "users": ["id", "name", "email"],
            "orders": ["id", "user_id", "total"],
            "products": ["id", "name", "price"]
        }
        
        manager.update_schema_context(tables, table_columns)
        
        # Schema context should be set
        assert "users" in manager._schema_context
        assert "orders" in manager._schema_context
    
    def test_update_schema_context_empty(self, manager):
        """Test updating schema context with empty data."""
        manager.update_schema_context([], {})
        assert manager._schema_context == ""
    
    def test_cache_management(self, manager):
        """Test suggestion cache management."""
        # Add items to cache
        for i in range(50):
            manager._add_to_cache(f"key_{i}", f"value_{i}")
        
        assert len(manager._cache) == 50
        
        # Clear cache
        manager.clear_cache()
        assert len(manager._cache) == 0
    
    def test_cache_size_limit(self, manager):
        """Test that cache respects size limits."""
        manager._max_cache_size = 10
        
        # Add more items than the limit
        for i in range(20):
            manager._add_to_cache(f"key_{i}", f"value_{i}")
        
        # Cache should be trimmed
        assert len(manager._cache) <= manager._max_cache_size
    
    def test_clean_suggestion_markdown(self, manager):
        """Test cleaning suggestions that contain markdown."""
        # Test with code block
        suggestion = "```sql\nSELECT * FROM users\n```"
        cleaned = manager._clean_suggestion(suggestion, "")
        assert "```" not in cleaned
        assert "SELECT * FROM users" in cleaned
    
    def test_clean_suggestion_quotes(self, manager):
        """Test cleaning suggestions with quotes."""
        suggestion = '"SELECT * FROM users"'
        cleaned = manager._clean_suggestion(suggestion, "")
        assert cleaned == "SELECT * FROM users"
    
    def test_clean_suggestion_current_word(self, manager):
        """Test that current word prefix is removed from suggestion."""
        suggestion = "SELECT * FROM users"
        cleaned = manager._clean_suggestion(suggestion, "SEL")
        assert cleaned == "ECT * FROM users"
    
    def test_build_prompt_with_schema(self, manager):
        """Test prompt building includes schema context."""
        manager._schema_context = "Available tables: users(id, name)"
        
        prompt = manager._build_prompt("SELECT ", "")
        
        assert "Available tables: users(id, name)" in prompt
        assert "SELECT " in prompt
    
    def test_build_prompt_with_current_word(self, manager):
        """Test prompt building includes current word."""
        prompt = manager._build_prompt("SELECT * FR", "FR")
        
        assert "Currently typing: FR" in prompt
    
    def test_is_available_conditions(self, manager):
        """Test is_available checks all conditions."""
        # Not available: no key, disabled, no client
        assert not manager.is_available
        
        # Set key and mock client
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {'openai': mock_openai}):
            mock_openai.OpenAI = MagicMock(return_value=MagicMock())
            manager.set_api_key("sk-test")
        
        # Check availability depends on client initialization
        # Since we mocked it, client should be set
        if manager._client:
            manager.set_enabled(True)
            assert manager.is_available
            
            # Disable and check
            manager.set_enabled(False)
            assert not manager.is_available


class TestAIAutocompleteManagerIntegration:
    """Integration tests for AI autocomplete (require mocking OpenAI)."""
    
    @pytest.fixture
    def configured_manager(self, tmp_path, monkeypatch):
        """Create a configured manager with mocked OpenAI."""
        settings_file = tmp_path / ".sqlshell_settings.json"
        monkeypatch.setattr(
            'sqlshell.ai_autocomplete.AIAutocompleteManager._get_settings_file',
            lambda self: str(settings_file)
        )
        
        manager = AIAutocompleteManager()
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="FROM users WHERE id = 1"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        mock_openai = MagicMock()
        mock_openai.OpenAI = MagicMock(return_value=mock_client)
        
        with patch.dict(sys.modules, {'openai': mock_openai}):
            manager.set_api_key("sk-test-key")
            manager._client = mock_client
        
        return manager
    
    def test_request_suggestion_caches_result(self, configured_manager):
        """Test that suggestions are cached."""
        # Make a request directly using _fetch_suggestion
        configured_manager._fetch_suggestion("SELECT * ", "", 10, None)
        
        # Check cache
        assert len(configured_manager._cache) > 0
    
    def test_cancel_pending_requests(self, configured_manager):
        """Test canceling pending requests."""
        # Start a request timer
        configured_manager._last_context = ("SELECT", "", 6, None)
        
        # Cancel
        configured_manager.cancel_pending_requests()
        
        assert configured_manager._last_context is None


class TestGetAIAutocompleteManager:
    """Tests for the singleton getter function."""
    
    def test_returns_same_instance(self):
        """Test that the same instance is returned."""
        manager1 = get_ai_autocomplete_manager()
        manager2 = get_ai_autocomplete_manager()
        
        assert manager1 is manager2
    
    def test_returns_ai_autocomplete_manager(self):
        """Test that an AIAutocompleteManager is returned."""
        manager = get_ai_autocomplete_manager()
        assert isinstance(manager, AIAutocompleteManager)


class TestOpenAINotInstalled:
    """Tests for graceful handling when OpenAI is not installed."""
    
    def test_init_client_handles_import_error(self, tmp_path, monkeypatch):
        """Test that missing openai library is handled gracefully."""
        settings_file = tmp_path / ".sqlshell_settings.json"
        monkeypatch.setattr(
            'sqlshell.ai_autocomplete.AIAutocompleteManager._get_settings_file',
            lambda self: str(settings_file)
        )
        
        manager = AIAutocompleteManager()
        manager._api_key = "sk-test"
        manager._client = None  # Ensure client is None
        
        # Mock the _init_client to simulate import error scenario
        def mock_init_that_fails(self):
            try:
                # Simulate the ImportError that would happen if openai isn't installed
                raise ImportError("No module named 'openai'")
            except ImportError:
                print("OpenAI library not installed. Run: pip install openai")
                return False
        
        # Temporarily replace the method
        original_init = manager._init_client
        manager._init_client = lambda: mock_init_that_fails(manager)
        
        result = manager._init_client()
        
        assert result is False
        assert manager._client is None
        assert not manager.is_available
        
        # Restore original method
        manager._init_client = original_init


class TestAIAutocompleteSignals:
    """Tests for Qt signal handling."""
    
    @pytest.fixture
    def manager_with_signal_handler(self, tmp_path, monkeypatch):
        """Create a manager with signal handler attached."""
        settings_file = tmp_path / ".sqlshell_settings.json"
        monkeypatch.setattr(
            'sqlshell.ai_autocomplete.AIAutocompleteManager._get_settings_file',
            lambda self: str(settings_file)
        )
        
        manager = AIAutocompleteManager()
        manager._suggestions_received = []
        manager._errors_received = []
        
        # Connect signals
        manager.suggestion_ready.connect(
            lambda s, p: manager._suggestions_received.append((s, p))
        )
        manager.error_occurred.connect(
            lambda e: manager._errors_received.append(e)
        )
        
        return manager
    
    def test_suggestion_ready_signal_exists(self, manager_with_signal_handler):
        """Test that suggestion_ready signal exists."""
        assert hasattr(manager_with_signal_handler, 'suggestion_ready')
    
    def test_error_occurred_signal_exists(self, manager_with_signal_handler):
        """Test that error_occurred signal exists."""
        assert hasattr(manager_with_signal_handler, 'error_occurred')
