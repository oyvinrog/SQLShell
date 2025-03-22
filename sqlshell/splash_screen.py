from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QMovie, QPainterPath, QLinearGradient
import os

class AnimatedSplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        # Initialize properties for animations first
        self._opacity = 0.0
        self._progress = 0.0
        self.next_widget = None
        
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
        
        # Create background container for the title and subtitle
        self.content_container = QWidget(self)
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)
        
        # Create title label
        self.title_label = QLabel("SQLShell", self.content_container)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #3498DB;
                font-size: 32px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
            }
        """)
        content_layout.addWidget(self.title_label)
        
        # Create subtitle label
        self.subtitle_label = QLabel("Loading...", self.content_container)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
            }
        """)
        content_layout.addWidget(self.subtitle_label)
        
        # Add content container to main layout
        layout.addWidget(self.content_container)
        
        # Create movie label (background)
        self.movie_label = QLabel(self)
        self.movie_label.setGeometry(0, 0, self.width(), self.height())
        self.movie_label.lower()  # Put it at the back
        
        # Create overlay for fade effect (between movie and content)
        self.overlay = QLabel(self)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.lower()  # Put it behind the content but above the movie
        
        # Create text label for animated text
        self.text_label = QLabel(self)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet("color: rgba(255, 255, 255, 0); background: transparent;")
        self.text_label.setGeometry(0, 0, self.width(), self.height())
        self.text_label.lower()  # Put it behind the content
        
        # Create progress bar (always on top)
        self.progress_bar = QLabel(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("background-color: #3498DB; border-radius: 2px;")
        self.progress_bar.move(100, self.height() - 40)
        self.progress_bar.setFixedWidth(0)
        self.progress_bar.raise_()  # Ensure it's on top
        
        # Set up the loading animation
        self.movie = QMovie(os.path.join(os.path.dirname(__file__), "resources", "splash_screen.gif"))
        self.movie.setScaledSize(self.size())
        self.movie_label.setMovie(self.movie)
        
        # Set up fade animation
        self.fade_anim = QPropertyAnimation(self, b"opacity")
        self.fade_anim.setDuration(1000)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Set up progress animation
        self.progress_anim = QPropertyAnimation(self, b"progress")
        self.progress_anim.setDuration(2000)
        self.progress_anim.setStartValue(0.0)
        self.progress_anim.setEndValue(1.0)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Start animations after everything is initialized
        QTimer.singleShot(100, self.start_animations)  # Small delay to ensure everything is ready

    def start_animations(self):
        """Start all animations"""
        self.movie.start()
        self.fade_anim.start()
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