"""
Modern notification system for SQLShell.
Provides non-blocking, toast-style notifications instead of modal dialogs.
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QGraphicsEffect, QGraphicsDropShadowEffect,
                             QApplication)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPalette, QFont, QIcon, QBrush, QPen, QPainterPath
import time
from typing import List, Optional
from enum import Enum


class NotificationType(Enum):
    """Types of notifications with different visual styles"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationWidget(QWidget):
    """A single notification widget with slide-in animation"""
    
    def __init__(self, message: str, notification_type: NotificationType, 
                 parent=None, duration: int = 5000):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        self.parent_widget = parent
        
        self.init_ui()
        self.setup_animations()
        
    def init_ui(self):
        """Initialize the notification UI"""
        self.setFixedHeight(80)
        self.setMinimumWidth(350)
        self.setMaximumWidth(500)
        
        # Make widget stay on top
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Store colors for painting
        self._bg_color = QColor('#E3F2FD')
        self._border_color = QColor('#2196F3')
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Icon label
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # Message label
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        font = QFont()
        font.setPointSize(10)
        self.message_label.setFont(font)
        layout.addWidget(self.message_label, 1)
        
        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(24, 24)
        self.close_button.clicked.connect(self.close_notification)
        layout.addWidget(self.close_button)
        
        # Apply styling based on notification type
        self.apply_styling()
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        
    def apply_styling(self):
        """Apply styling based on notification type"""
        styles = {
            NotificationType.INFO: {
                'bg_color': '#E3F2FD',  # Light blue background
                'text_color': '#0D47A1',  # Dark blue text
                'border_color': '#2196F3',
                'icon': 'ℹ'
            },
            NotificationType.SUCCESS: {
                'bg_color': '#E8F5E9',  # Light green background
                'text_color': '#1B5E20',  # Dark green text
                'border_color': '#4CAF50',
                'icon': '✓'
            },
            NotificationType.WARNING: {
                'bg_color': '#FFF3E0',  # Light orange background
                'text_color': '#E65100',  # Dark orange text
                'border_color': '#FF9800',
                'icon': '⚠'
            },
            NotificationType.ERROR: {
                'bg_color': '#FFEBEE',  # Light red background
                'text_color': '#B71C1C',  # Dark red text
                'border_color': '#F44336',
                'icon': '✗'
            }
        }
        
        style = styles[self.notification_type]
        
        # Store colors for custom painting (solid background)
        self._bg_color = QColor(style['bg_color'])
        self._border_color = QColor(style['border_color'])
        
        # Set icon with improved visibility
        self.icon_label.setText(style['icon'])
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                color: {style['text_color']};
                font-size: 18px;
                font-weight: bold;
                font-family: "Arial", "Helvetica", sans-serif;
                background: transparent;
            }}
        """)
        
        # Set message styling with improved readability
        self.message_label.setStyleSheet(f"""
            QLabel {{
                color: {style['text_color']};
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                font-family: "Arial", "Helvetica", sans-serif;
                padding: 2px;
            }}
        """)
        
        # Set close button styling
        self.close_button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {style['text_color']};
                font-size: 14px;
                font-weight: bold;
                border-radius: 12px;
                font-family: "Arial", "Helvetica", sans-serif;
            }}
            QPushButton:hover {{
                background: rgba(0, 0, 0, 0.1);
            }}
            QPushButton:pressed {{
                background: rgba(0, 0, 0, 0.2);
            }}
        """)
        
    def paintEvent(self, event):
        """Paint a solid opaque background with rounded corners"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        rect = self.rect().adjusted(2, 2, -2, -2)  # Leave room for border
        path.addRoundedRect(float(rect.x()), float(rect.y()), 
                           float(rect.width()), float(rect.height()), 8, 8)
        
        # Fill with solid opaque background
        painter.fillPath(path, QBrush(self._bg_color))
        
        # Draw border
        painter.setPen(QPen(self._border_color, 3))
        painter.drawPath(path)
        
    def setup_animations(self):
        """Setup slide-in and fade-out animations"""
        # Slide in animation
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_animation.setDuration(300)
        
        # Fade out animation  
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.setDuration(200)
        self.fade_animation.finished.connect(self.hide)
        
        # Auto-hide timer
        if self.duration > 0:
            self.auto_hide_timer = QTimer()
            self.auto_hide_timer.timeout.connect(self.close_notification)
            self.auto_hide_timer.setSingleShot(True)
            
    def show_notification(self, position: QRect):
        """Show the notification with slide-in animation"""
        # Position is already in global screen coordinates
        # Start position: slide in from the right (off screen)
        start_rect = QRect(position.x() + 400, position.y(), 
                          self.width(), self.height())
        end_rect = QRect(position.x(), position.y(),
                        self.width(), self.height())
        
        self.setGeometry(start_rect)
        self.show()
        
        # Animate slide in
        self.slide_animation.setStartValue(start_rect)
        self.slide_animation.setEndValue(end_rect)
        self.slide_animation.start()
        
        # Start auto-hide timer
        if self.duration > 0:
            self.auto_hide_timer.start(self.duration)
            
    def close_notification(self):
        """Close the notification with fade-out animation"""
        if hasattr(self, 'auto_hide_timer'):
            self.auto_hide_timer.stop()
            
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
        
    def enterEvent(self, event):
        """Pause auto-hide when mouse enters"""
        if hasattr(self, 'auto_hide_timer'):
            self.auto_hide_timer.stop()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Resume auto-hide when mouse leaves"""
        if hasattr(self, 'auto_hide_timer') and self.duration > 0:
            self.auto_hide_timer.start(2000)  # Shorter duration after hover
        super().leaveEvent(event)


class NotificationManager:
    """Manages multiple notifications and their positioning"""
    
    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
        self.notifications: List[NotificationWidget] = []
        self.notification_spacing = 10
        
    def show_notification(self, message: str, notification_type: NotificationType,
                         duration: int = 5000) -> NotificationWidget:
        """Show a new notification"""
        # Clean up any hidden notifications
        self._cleanup_notifications()
        
        # Create new notification
        notification = NotificationWidget(
            message=message,
            notification_type=notification_type,
            parent=self.parent_widget,
            duration=duration
        )
        
        # Calculate position for this notification
        position = self._calculate_position(notification)
        
        # Connect cleanup when notification is hidden
        notification.fade_animation.finished.connect(
            lambda: self._remove_notification(notification)
        )
        
        # Add to our list and show
        self.notifications.append(notification)
        notification.show_notification(position)
        
        return notification
        
    def show_info(self, message: str, duration: int = 5000) -> NotificationWidget:
        """Show an info notification"""
        return self.show_notification(message, NotificationType.INFO, duration)
        
    def show_success(self, message: str, duration: int = 4000) -> NotificationWidget:
        """Show a success notification"""
        return self.show_notification(message, NotificationType.SUCCESS, duration)
        
    def show_warning(self, message: str, duration: int = 6000) -> NotificationWidget:
        """Show a warning notification"""
        return self.show_notification(message, NotificationType.WARNING, duration)
        
    def show_error(self, message: str, duration: int = 8000) -> NotificationWidget:
        """Show an error notification"""
        return self.show_notification(message, NotificationType.ERROR, duration)
        
    def _calculate_position(self, notification: NotificationWidget) -> QRect:
        """Calculate the position for a new notification (in global screen coordinates)"""
        # Get the parent widget's global position on screen
        parent_global_pos = self.parent_widget.mapToGlobal(QPoint(0, 0))
        parent_width = self.parent_widget.width()
        
        # Calculate position relative to parent's right edge (in screen coordinates)
        # Position notification inside the parent window's right side
        x = parent_global_pos.x() + parent_width - notification.width() - 20
        y = parent_global_pos.y() + 80  # Start below any toolbar/menubar
        
        # Stack notifications vertically
        for existing in self.notifications:
            if existing.isVisible():
                y += existing.height() + self.notification_spacing
                
        return QRect(x, y, notification.width(), notification.height())
        
    def _remove_notification(self, notification: NotificationWidget):
        """Remove a notification from the list"""
        if notification in self.notifications:
            self.notifications.remove(notification)
            notification.deleteLater()
            
    def _cleanup_notifications(self):
        """Remove any notifications that are no longer visible"""
        self.notifications = [n for n in self.notifications if n.isVisible()]
        
    def clear_all(self):
        """Clear all notifications"""
        for notification in self.notifications[:]:
            notification.close_notification()
        self.notifications.clear()


# Global instance to be used throughout the application
_notification_manager: Optional[NotificationManager] = None


def init_notification_manager(parent_widget):
    """Initialize the global notification manager"""
    global _notification_manager
    _notification_manager = NotificationManager(parent_widget)
    

def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance"""
    global _notification_manager
    if _notification_manager is None:
        raise RuntimeError("Notification manager not initialized. Call init_notification_manager() first.")
    return _notification_manager


def show_info_notification(message: str, duration: int = 5000):
    """Convenience function to show info notification"""
    return get_notification_manager().show_info(message, duration)


def show_success_notification(message: str, duration: int = 4000):
    """Convenience function to show success notification"""
    return get_notification_manager().show_success(message, duration)


def show_warning_notification(message: str, duration: int = 6000):
    """Convenience function to show warning notification"""
    return get_notification_manager().show_warning(message, duration)


def show_error_notification(message: str, duration: int = 8000):
    """Convenience function to show error notification"""
    return get_notification_manager().show_error(message, duration)