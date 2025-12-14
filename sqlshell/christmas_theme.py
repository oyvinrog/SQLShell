"""
Christmas Theme module for SQLShell.
Adds festive decorations to the application window.
"""

import os
import random
from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PyQt6.QtGui import QPixmap


def get_resource_path(filename):
    """Get the full path to a Christmas theme resource."""
    return os.path.join(
        os.path.dirname(__file__), 
        "resources", 
        "christmas_theme", 
        filename
    )


class ChristmasDecoration(QLabel):
    """A floating Christmas decoration widget."""
    
    def __init__(self, parent, image_path, scale=0.3):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Load and scale the image
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled_width = int(pixmap.width() * scale)
            scaled_height = int(pixmap.height() * scale)
            scaled_pixmap = pixmap.scaled(
                scaled_width, scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            self.setFixedSize(scaled_pixmap.size())
        
        self.raise_()
        self.show()


class SnowflakeWidget(QLabel):
    """An animated falling snowflake."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setText("❄")
        self.setStyleSheet("""
            color: white;
            font-size: 20px;
            background: transparent;
        """)
        self.adjustSize()
        
        # Random horizontal position
        self.x_pos = random.randint(0, parent.width() - 20)
        self.y_pos = -30
        self.move(self.x_pos, self.y_pos)
        
        # Random fall speed and horizontal drift
        self.fall_speed = random.uniform(1, 3)
        self.drift = random.uniform(-0.5, 0.5)
        self.show()
    
    def update_position(self):
        """Update snowflake position for animation."""
        self.y_pos += self.fall_speed
        self.x_pos += self.drift
        self.move(int(self.x_pos), int(self.y_pos))
        
        # Return True if still visible
        return self.y_pos < self.parent().height() + 30


class ChristmasThemeManager:
    """Manages Christmas theme decorations for the main window."""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.decorations = []
        self.snowflakes = []
        self.snow_timer = None
        self.animation_timer = None
        self.enabled = False
    
    def enable(self):
        """Enable the Christmas theme with decorations."""
        if self.enabled:
            return
        
        self.enabled = True
        self._add_corner_decorations()
        self._start_snow_animation()
    
    def disable(self):
        """Disable the Christmas theme and remove all decorations."""
        if not self.enabled:
            return
        
        self.enabled = False
        
        # Stop timers
        if self.snow_timer:
            self.snow_timer.stop()
            self.snow_timer = None
        
        if self.animation_timer:
            self.animation_timer.stop()
            self.animation_timer = None
        
        # Remove all decorations
        for decoration in self.decorations:
            decoration.hide()
            decoration.deleteLater()
        self.decorations.clear()
        
        # Remove all snowflakes
        for snowflake in self.snowflakes:
            snowflake.hide()
            snowflake.deleteLater()
        self.snowflakes.clear()
    
    def toggle(self):
        """Toggle the Christmas theme on/off."""
        if self.enabled:
            self.disable()
        else:
            self.enable()
        return self.enabled
    
    def _add_corner_decorations(self):
        """Add decorations to the corners of the window."""
        # Top-left: Santa hat on the window
        santa_hat = ChristmasDecoration(
            self.main_window,
            get_resource_path("santa_hat.png"),
            scale=0.25
        )
        santa_hat.move(5, -5)
        self.decorations.append(santa_hat)
        
        # Top-right: Pine branch with ornaments
        pine_branch = ChristmasDecoration(
            self.main_window,
            get_resource_path("pine_branch.png"),
            scale=0.3
        )
        pine_branch.move(
            self.main_window.width() - pine_branch.width() - 10,
            -10
        )
        self.decorations.append(pine_branch)
        
        # Top-left (lower): Holly
        holly = ChristmasDecoration(
            self.main_window,
            get_resource_path("holly_large.png"),
            scale=0.2
        )
        holly.move(self.main_window.width() // 3, 5)
        self.decorations.append(holly)
        
        # Top-right (lower): Bow
        bow = ChristmasDecoration(
            self.main_window,
            get_resource_path("bow.png"),
            scale=0.2
        )
        bow.move(self.main_window.width() // 3 * 2, 5)
        self.decorations.append(bow)
        
        # Bottom-left: Gift box
        gift = ChristmasDecoration(
            self.main_window,
            get_resource_path("gift_box.png"),
            scale=0.25
        )
        gift.move(10, self.main_window.height() - gift.height() - 40)
        self.decorations.append(gift)
        
        # Bottom-right: Wreath
        wreath = ChristmasDecoration(
            self.main_window,
            get_resource_path("wreath.png"),
            scale=0.25
        )
        wreath.move(
            self.main_window.width() - wreath.width() - 10,
            self.main_window.height() - wreath.height() - 40
        )
        self.decorations.append(wreath)
        
        # Bottom-center: Snowman
        snowman = ChristmasDecoration(
            self.main_window,
            get_resource_path("snowman.png"),
            scale=0.2
        )
        snowman.move(
            (self.main_window.width() - snowman.width()) // 2,
            self.main_window.height() - snowman.height() - 35
        )
        self.decorations.append(snowman)
    
    def _start_snow_animation(self):
        """Start the falling snow animation."""
        # Timer to create new snowflakes
        self.snow_timer = QTimer(self.main_window)
        self.snow_timer.timeout.connect(self._create_snowflake)
        self.snow_timer.start(300)  # New snowflake every 300ms
        
        # Timer to animate existing snowflakes
        self.animation_timer = QTimer(self.main_window)
        self.animation_timer.timeout.connect(self._animate_snowflakes)
        self.animation_timer.start(50)  # Update every 50ms for smooth animation
    
    def _create_snowflake(self):
        """Create a new snowflake at a random horizontal position."""
        if len(self.snowflakes) < 50:  # Limit maximum snowflakes
            snowflake = SnowflakeWidget(self.main_window)
            self.snowflakes.append(snowflake)
    
    def _animate_snowflakes(self):
        """Update all snowflake positions."""
        # Update positions and remove those that have fallen off screen
        still_visible = []
        for snowflake in self.snowflakes:
            if snowflake.update_position():
                still_visible.append(snowflake)
            else:
                snowflake.hide()
                snowflake.deleteLater()
        self.snowflakes = still_visible
    
    def update_positions(self):
        """Update decoration positions when window is resized."""
        if not self.enabled or not self.decorations:
            return
        
        # Re-add decorations at correct positions
        self.disable()
        self.enable()
