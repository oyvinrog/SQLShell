from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QMovie, QPainterPath, QLinearGradient
import os

class AnimatedSplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        # Set up the window properties
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )
        
        # Set widget attributes for proper compositing
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # Set fixed size
        self.setFixedSize(400, 300)
        
        # Center the splash screen on the screen
        screen_geometry = self.screen().geometry()
        self.move(
            (screen_geometry.width() - self.width()) // 2,
            (screen_geometry.height() - self.height()) // 2
        )

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Create title label
        self.title_label = QLabel("SQLShell", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #3498DB;
                font-size: 32px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Create subtitle label
        self.subtitle_label = QLabel("Loading...", self)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.subtitle_label)
        
        # Initialize properties for animations
        self._opacity = 0.0
        self._progress = 0.0
        
        # Start animations when shown
        self.start_animations()

    def start_animations(self):
        """Start all animations"""
        print("Starting animations...")
        self.movie.start()
        print(f"Movie state: {self.movie.state()}")
        print(f"Starting fade animation from {self.fade_anim.startValue()} to {self.fade_anim.endValue()}")
        self.fade_anim.start()
        print(f"Starting progress animation from {self.progress_anim.startValue()} to {self.progress_anim.endValue()}")
        self.progress_anim.start()
        self.progress_anim.finished.connect(self._on_animation_finished)

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        # Update opacity of overlay and text
        self.overlay.setStyleSheet(f"background-color: rgba(0, 0, 0, {int(100 * value)});")
        self.text_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, {int(255 * value)});
                background: transparent;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, {int(180 * value)}),
                            0px 0px 10px rgba(52, 152, 219, {int(160 * value)});
            }}
        """)

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        # Update progress bar width
        self.progress_bar.setFixedWidth(int(200 * value))

    def _on_animation_finished(self):
        """Handle animation completion"""
        if self.next_widget:
            QTimer.singleShot(500, self._finish_splash)

    def _finish_splash(self):
        """Clean up and show the main window"""
        self.movie.stop()
        self.fade_anim.stop()
        self.progress_anim.stop()
        self.close()
        if self.next_widget:
            self.next_widget.show()

    def finish(self, widget):
        """Store the widget to show after animation completes"""
        self.next_widget = widget 