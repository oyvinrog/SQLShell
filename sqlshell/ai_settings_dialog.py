"""
AI Settings Dialog for SQLShell.

This module provides a dialog for configuring OpenAI API settings
for the AI autocomplete feature.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QComboBox, QGroupBox, QMessageBox,
    QFormLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from sqlshell.ai_autocomplete import get_ai_autocomplete_manager


class AISettingsDialog(QDialog):
    """Dialog for configuring AI autocomplete settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_manager = get_ai_autocomplete_manager()
        self.setWindowTitle("AI Autocomplete Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("🤖 AI-Powered SQL Autocomplete")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "Enable intelligent SQL suggestions powered by OpenAI. "
            "This feature uses GPT models to provide context-aware completions "
            "based on your database schema and query context."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)
        
        # Enable/Disable checkbox
        self.enabled_checkbox = QCheckBox("Enable AI Autocomplete")
        self.enabled_checkbox.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.enabled_checkbox)
        
        # API Key group
        api_group = QGroupBox("OpenAI API Configuration")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(12)
        
        # API Key input
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setMinimumWidth(300)
        api_key_layout.addWidget(self.api_key_input)
        
        self.show_key_btn = QPushButton("👁")
        self.show_key_btn.setFixedWidth(40)
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self.toggle_key_visibility)
        self.show_key_btn.setToolTip("Show/Hide API Key")
        api_key_layout.addWidget(self.show_key_btn)
        
        api_layout.addRow("API Key:", api_key_layout)
        
        # API key help text
        help_label = QLabel(
            '<a href="https://platform.openai.com/api-keys">Get your API key from OpenAI</a>'
        )
        help_label.setOpenExternalLinks(True)
        help_label.setStyleSheet("color: #1890ff; font-size: 11px;")
        api_layout.addRow("", help_label)
        
        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ])
        self.model_combo.setToolTip(
            "gpt-4o-mini: Fast and cost-effective (recommended)\n"
            "gpt-4o: Most capable, higher cost\n"
            "gpt-4-turbo: Good balance of capability and speed\n"
            "gpt-3.5-turbo: Fastest, lowest cost"
        )
        api_layout.addRow("Model:", self.model_combo)
        
        layout.addWidget(api_group)
        
        # Status indicator
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        
        self.status_icon = QLabel("⚪")
        self.status_icon.setFixedWidth(24)
        status_layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("Not configured")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        status_layout.addWidget(self.test_btn)
        
        layout.addWidget(self.status_frame)
        
        # Info about usage
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #e6f7ff;
                border: 1px solid #91d5ff;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        info_label = QLabel(
            "💡 <b>How it works:</b><br>"
            "• AI suggestions appear as ghost text while you type<br>"
            "• Press <b>Tab</b> to accept a suggestion<br>"
            "• The AI uses your table schema for context-aware completions<br>"
            "• API calls are rate-limited and cached for efficiency"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #0050b3;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_frame)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
        """)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def toggle_key_visibility(self, visible: bool):
        """Toggle API key visibility."""
        if visible:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("🔒")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("👁")
    
    def load_settings(self):
        """Load current settings into the dialog."""
        # Load enabled state
        self.enabled_checkbox.setChecked(self.ai_manager.is_enabled())
        
        # Load API key (raw for editing)
        raw_key = self.ai_manager.get_raw_api_key()
        if raw_key:
            self.api_key_input.setText(raw_key)
        
        # Load model
        current_model = self.ai_manager.get_model()
        index = self.model_combo.findText(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        # Update status
        self.update_status()
    
    def update_status(self):
        """Update the status indicator."""
        if self.ai_manager.is_available:
            self.status_icon.setText("🟢")
            self.status_label.setText("Ready - AI autocomplete is active")
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #f6ffed;
                    border: 1px solid #b7eb8f;
                    border-radius: 4px;
                }
            """)
        elif self.ai_manager.is_configured:
            self.status_icon.setText("🟡")
            self.status_label.setText("Configured but not validated")
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #fffbe6;
                    border: 1px solid #ffe58f;
                    border-radius: 4px;
                }
            """)
        else:
            self.status_icon.setText("⚪")
            self.status_label.setText("Not configured - enter your API key")
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    border-radius: 4px;
                }
            """)
    
    def test_connection(self):
        """Test the OpenAI API connection."""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Please enter an API key first.")
            return
        
        # Temporarily set the key for testing
        old_key = self.ai_manager.get_raw_api_key()
        self.ai_manager.set_api_key(api_key)
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # Make a minimal API call to test
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            
            if response.choices:
                QMessageBox.information(
                    self, 
                    "Connection Successful", 
                    "✅ Successfully connected to OpenAI API!\n\n"
                    "AI autocomplete is ready to use."
                )
                self.update_status()
            else:
                raise Exception("No response received")
                
        except ImportError:
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "The OpenAI library is not installed.\n\n"
                "Please run: pip install openai"
            )
            # Restore old key
            if old_key:
                self.ai_manager.set_api_key(old_key)
        except Exception as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower() or "incorrect api key" in error_msg.lower():
                QMessageBox.critical(
                    self,
                    "Invalid API Key",
                    "❌ The API key is invalid.\n\n"
                    "Please check your API key and try again."
                )
            elif "rate" in error_msg.lower():
                QMessageBox.warning(
                    self,
                    "Rate Limited",
                    "⚠️ Rate limited by OpenAI.\n\n"
                    "The key appears valid but you've hit the rate limit. "
                    "Please wait a moment and try again."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Connection Failed",
                    f"❌ Failed to connect to OpenAI:\n\n{error_msg}"
                )
            # Restore old key on failure
            if old_key != api_key:
                self.ai_manager.set_api_key(old_key)
    
    def save_settings(self):
        """Save the settings and close the dialog."""
        # Save API key
        api_key = self.api_key_input.text().strip()
        self.ai_manager.set_api_key(api_key)
        
        # Save enabled state
        self.ai_manager.set_enabled(self.enabled_checkbox.isChecked())
        
        # Save model selection
        self.ai_manager.set_model(self.model_combo.currentText())
        
        self.accept()


def show_ai_settings_dialog(parent=None):
    """Show the AI settings dialog."""
    dialog = AISettingsDialog(parent)
    return dialog.exec()

