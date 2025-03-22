from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QMovie, QPainterPath, QLinearGradient
import os

class AnimatedSplashScreen(QWidget):
    def __init__(self, gif_path):
        super().__init__()
        
        # Debug print
        print(f"Loading splash screen GIF from: {gif_path}")
        print(f"File exists: {os.path.exists(gif_path)}")
        
        # Set up the window properties
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )
        print(f"Window flags set: {self.windowFlags()}")  # Debug print
        
        # Set widget attributes for proper compositing
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        print(f"Translucent background attribute: {self.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)}")  # Debug print
        
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create background label for GIF
        self.movie_label = QLabel(self)
        self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie_label.setFixedSize(self.size())
        
        # Set up the movie
        self.movie = QMovie(gif_path)
        if not self.movie.isValid():
            print(f"Error loading movie: {self.movie.lastErrorString()}")
        self.movie.setScaledSize(self.size())
        self.movie_label.setMovie(self.movie)
        
        # Create semi-transparent overlay
        self.overlay = QLabel(self)
        self.overlay.setFixedSize(self.size())
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        
        # Create text label
        self.text_label = QLabel("SQL Shell", self)
        self.text_label.setFixedSize(self.size())
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set up font
        try:
            font = QFont("Segoe UI", 48, QFont.Weight.Bold)
        except:
            font = QFont("Arial", 48, QFont.Weight.Bold)
        self.text_label.setFont(font)
        
        # Style the text label
        self.text_label.setStyleSheet("""
            QLabel {
                color: white;
                background: transparent;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 180),
                            0px 0px 10px rgba(52, 152, 219, 160);
            }
        """)
        
        # Create progress bar background
        self.progress_bg = QLabel(self)
        self.progress_bg.setFixedSize(200, 4)
        self.progress_bg.move((self.width() - 200) // 2, self.height() - 30)
        self.progress_bg.setStyleSheet("background-color: rgba(52, 73, 94, 255);")
        
        # Create progress bar
        self.progress_bar = QLabel(self)
        self.progress_bar.setFixedSize(0, 4)  # Start with 0 width
        self.progress_bar.move((self.width() - 200) // 2, self.height() - 30)
        self.progress_bar.setStyleSheet("background-color: rgba(52, 152, 219, 255);")
        
        # Initialize animation properties
        self._opacity = 0.0
        self._progress = 0.0
        
        # Create opacity animation
        self.fade_anim = QPropertyAnimation(self, b"opacity")
        self.fade_anim.setDuration(1500)  # 1.5 seconds fade-in
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Create progress animation
        self.progress_anim = QPropertyAnimation(self, b"progress")
        self.progress_anim.setDuration(3000)  # 3 seconds progress
        self.progress_anim.setStartValue(0.0)
        self.progress_anim.setEndValue(1.0)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Store the widget to show later
        self.next_widget = None
        
        # Start animations with a slight delay
        QTimer.singleShot(100, self.start_animations)

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