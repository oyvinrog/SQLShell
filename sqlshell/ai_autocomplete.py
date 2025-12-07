"""
AI-powered SQL autocomplete using OpenAI API.

This module provides intelligent SQL suggestions using OpenAI's GPT models
when an API key is configured.
"""

import os
import json
import threading
from typing import Optional, Callable, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class AIAutocompleteManager(QObject):
    """
    Manages AI-powered SQL autocomplete suggestions using OpenAI.
    
    This class handles:
    - API key storage and validation
    - Async requests to OpenAI
    - Caching of suggestions for performance
    - Integration with the editor's ghost text system
    """
    
    # Signal emitted when AI suggestion is ready
    suggestion_ready = pyqtSignal(str, int)  # suggestion text, cursor position
    
    # Signal emitted when there's an error
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self._api_key: Optional[str] = None
        self._client = None
        self._enabled = True
        self._model = "gpt-4o-mini"  # Default to cost-effective model
        self._pending_request: Optional[threading.Thread] = None
        self._request_timer: Optional[QTimer] = None
        self._last_context = ""
        self._cache: Dict[str, str] = {}
        self._max_cache_size = 100
        self._schema_context = ""  # Store table/column info for context
        
        # Debounce settings
        self._debounce_ms = 500  # Wait 500ms after last keystroke
        
        # Load settings
        self._load_settings()
    
    def _get_settings_file(self) -> str:
        """Get the path to the settings file."""
        return os.path.join(os.path.expanduser('~'), '.sqlshell_settings.json')
    
    def _load_settings(self) -> None:
        """Load AI settings from the settings file."""
        try:
            settings_file = self._get_settings_file()
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    ai_settings = settings.get('ai_autocomplete', {})
                    self._api_key = ai_settings.get('api_key')
                    self._enabled = ai_settings.get('enabled', True)
                    self._model = ai_settings.get('model', 'gpt-4o-mini')
                    
                    # Initialize OpenAI client if API key is available
                    if self._api_key:
                        self._init_client()
        except Exception as e:
            print(f"Error loading AI settings: {e}")
    
    def _save_settings(self) -> None:
        """Save AI settings to the settings file."""
        try:
            settings_file = self._get_settings_file()
            settings = {}
            
            # Load existing settings
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            
            # Update AI settings
            settings['ai_autocomplete'] = {
                'api_key': self._api_key,
                'enabled': self._enabled,
                'model': self._model
            }
            
            # Save settings
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving AI settings: {e}")
    
    def _init_client(self) -> bool:
        """Initialize the OpenAI client."""
        if not self._api_key:
            return False
        
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
            return True
        except ImportError:
            print("OpenAI library not installed. Run: pip install openai")
            return False
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if AI autocomplete is available and enabled."""
        return self._enabled and self._api_key is not None and self._client is not None
    
    @property
    def is_configured(self) -> bool:
        """Check if an API key is configured (even if not valid)."""
        return self._api_key is not None and len(self._api_key) > 0
    
    def set_api_key(self, api_key: str) -> bool:
        """
        Set the OpenAI API key.
        
        Args:
            api_key: The OpenAI API key
            
        Returns:
            True if the key was set successfully
        """
        self._api_key = api_key if api_key and api_key.strip() else None
        success = self._init_client() if self._api_key else True
        self._save_settings()
        return success
    
    def get_api_key(self) -> Optional[str]:
        """Get the current API key (masked for display)."""
        if not self._api_key:
            return None
        # Return masked version for security
        if len(self._api_key) > 8:
            return self._api_key[:4] + "*" * (len(self._api_key) - 8) + self._api_key[-4:]
        return "*" * len(self._api_key)
    
    def get_raw_api_key(self) -> Optional[str]:
        """Get the raw API key (for internal use only)."""
        return self._api_key
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable AI autocomplete."""
        self._enabled = enabled
        self._save_settings()
    
    def is_enabled(self) -> bool:
        """Check if AI autocomplete is enabled."""
        return self._enabled
    
    def set_model(self, model: str) -> None:
        """Set the OpenAI model to use."""
        self._model = model
        self._save_settings()
    
    def get_model(self) -> str:
        """Get the current OpenAI model."""
        return self._model
    
    def update_schema_context(self, tables: List[str], table_columns: Dict[str, List[str]]) -> None:
        """
        Update the schema context for better suggestions.
        
        Args:
            tables: List of table names
            table_columns: Dictionary mapping table names to column lists
        """
        if not tables:
            self._schema_context = ""
            return
        
        # Build a compact schema description
        schema_parts = []
        for table in tables:
            columns = table_columns.get(table, [])
            if columns:
                cols_str = ", ".join(columns[:20])  # Limit columns to avoid token explosion
                if len(columns) > 20:
                    cols_str += f", ... ({len(columns) - 20} more)"
                schema_parts.append(f"{table}({cols_str})")
            else:
                schema_parts.append(table)
        
        self._schema_context = "Available tables: " + "; ".join(schema_parts[:15])  # Limit tables too
        if len(tables) > 15:
            self._schema_context += f" ... and {len(tables) - 15} more tables"
    
    def request_suggestion(self, text_before_cursor: str, current_word: str, 
                          cursor_position: int, callback: Optional[Callable] = None) -> None:
        """
        Request an AI suggestion for the current context.
        
        This method debounces requests to avoid excessive API calls.
        
        Args:
            text_before_cursor: The SQL text before the cursor
            current_word: The current word being typed
            cursor_position: The current cursor position
            callback: Optional callback function for the result
        """
        if not self.is_available:
            return
        
        # Create cache key
        cache_key = f"{text_before_cursor}|{current_word}"
        
        # Check cache first
        if cache_key in self._cache:
            suggestion = self._cache[cache_key]
            if suggestion:
                self.suggestion_ready.emit(suggestion, cursor_position)
            return
        
        # Cancel any pending request
        if self._request_timer:
            self._request_timer.stop()
        
        # Store context for debounced request
        self._last_context = (text_before_cursor, current_word, cursor_position, callback)
        
        # Create debounce timer
        self._request_timer = QTimer()
        self._request_timer.setSingleShot(True)
        self._request_timer.timeout.connect(self._execute_request)
        self._request_timer.start(self._debounce_ms)
    
    def _execute_request(self) -> None:
        """Execute the actual API request in a background thread."""
        if not self._last_context:
            return
        
        text_before_cursor, current_word, cursor_position, callback = self._last_context
        
        print(f"[AI] Executing request, context length: {len(text_before_cursor)}")
        
        # Run API request in background thread
        thread = threading.Thread(
            target=self._fetch_suggestion,
            args=(text_before_cursor, current_word, cursor_position, callback),
            daemon=True
        )
        thread.start()
        self._pending_request = thread
    
    def _fetch_suggestion(self, text_before_cursor: str, current_word: str,
                         cursor_position: int, callback: Optional[Callable]) -> None:
        """Fetch suggestion from OpenAI API (runs in background thread)."""
        try:
            if not self._client:
                return
            
            # Build the prompt
            prompt = self._build_prompt(text_before_cursor, current_word)
            
            # Make the API call
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a SQL autocomplete assistant. Complete the SQL query "
                            "based on the context. Return ONLY the completion text that should "
                            "be inserted after the cursor - no explanation, no markdown, no "
                            "code blocks. If the user is mid-word, complete that word. "
                            "Keep completions concise and contextually appropriate. "
                            "If unsure, provide a common SQL pattern that fits the context."
                        )
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=100,
                temperature=0.3,  # Lower temperature for more predictable completions
                stop=[";", "\n\n"]  # Stop at statement end or double newline
            )
            
            suggestion = response.choices[0].message.content.strip()
            
            # Clean up suggestion
            suggestion = self._clean_suggestion(suggestion, current_word)
            
            if suggestion:
                # Cache the result
                cache_key = f"{text_before_cursor}|{current_word}"
                self._add_to_cache(cache_key, suggestion)
                
                print(f"[AI] Got suggestion: '{suggestion[:50]}...' at position {cursor_position}")
                
                # Emit signal (Qt will handle thread safety)
                self.suggestion_ready.emit(suggestion, cursor_position)
                
                # Call callback if provided
                if callback:
                    callback(suggestion, cursor_position)
                    
        except Exception as e:
            error_msg = str(e)
            # Don't spam errors for rate limits or network issues
            if "rate" not in error_msg.lower() and "connection" not in error_msg.lower():
                print(f"AI autocomplete error: {e}")
            self.error_occurred.emit(error_msg)
    
    def _build_prompt(self, text_before_cursor: str, current_word: str) -> str:
        """Build the prompt for the AI model."""
        parts = []
        
        # Add schema context if available
        if self._schema_context:
            parts.append(self._schema_context)
        
        # Add the SQL context
        parts.append(f"SQL query so far:\n{text_before_cursor}")
        
        if current_word:
            parts.append(f"Currently typing: {current_word}")
        
        parts.append("Complete the SQL (return only the completion text):")
        
        return "\n\n".join(parts)
    
    def _clean_suggestion(self, suggestion: str, current_word: str) -> str:
        """Clean up the AI suggestion."""
        if not suggestion:
            return ""
        
        # Remove markdown code blocks if present
        if suggestion.startswith("```"):
            lines = suggestion.split("\n")
            # Find content between ``` markers
            content_lines = []
            in_code = False
            for line in lines:
                if line.startswith("```"):
                    in_code = not in_code
                    continue
                if in_code or not suggestion.count("```"):
                    content_lines.append(line)
            suggestion = "\n".join(content_lines).strip()
        
        # Remove leading/trailing quotes
        suggestion = suggestion.strip('"\'`')
        
        # If suggestion starts with the current word, remove it to avoid duplication
        if current_word and suggestion.lower().startswith(current_word.lower()):
            suggestion = suggestion[len(current_word):]
        
        return suggestion.strip()
    
    def _add_to_cache(self, key: str, value: str) -> None:
        """Add a suggestion to the cache, managing cache size."""
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._cache.keys())[:self._max_cache_size // 2]
            for k in keys_to_remove:
                del self._cache[k]
        
        self._cache[key] = value
    
    def clear_cache(self) -> None:
        """Clear the suggestion cache."""
        self._cache.clear()
    
    def cancel_pending_requests(self) -> None:
        """Cancel any pending AI requests."""
        if self._request_timer:
            self._request_timer.stop()
        self._last_context = None


# Singleton instance
_ai_manager: Optional[AIAutocompleteManager] = None


def get_ai_autocomplete_manager() -> AIAutocompleteManager:
    """Get the global AI autocomplete manager instance."""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIAutocompleteManager()
    return _ai_manager

