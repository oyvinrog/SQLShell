from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QMovie, QPainterPath, QLinearGradient, QPixmap
import os

class AnimatedSplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        # Initialize properties for animations first
        self._opacity = 0.0
        self._progress = 0.0
        self.next_widget = None
        self.use_fallback = False
        
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

        # Create movie label first (background)
        self.movie_label = QLabel(self)
        self.movie_label.setGeometry(0, 0, self.width(), self.height())
        
        # Create overlay for fade effect (between movie and content)
        self.overlay = QLabel(self)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        
        # Create text label for animated text
        self.text_label = QLabel(self)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet("color: rgba(255, 255, 255, 0); background: transparent;")
        self.text_label.setGeometry(0, 0, self.width(), self.height())

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Create background container for the title and subtitle
        self.content_container = QWidget(self)
        self.content_container.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)
        
        # Add logo above the title
        self.logo_label = QLabel(self.content_container)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load logo from resources directory
        logo_path = os.path.join(os.path.dirname(__file__), "resources", "logo_small.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            # Scale logo to appropriate size for splash screen
            scaled_logo = logo_pixmap.scaledToHeight(64, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_logo)
        
        content_layout.addWidget(self.logo_label)
        
        # Create title label
        self.title_label = QLabel("SQLShell", self.content_container)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #3498DB;
                font-size: 28px;
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
        
        # Create progress bar (always on top)
        self.progress_bar = QLabel(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("background-color: #3498DB; border-radius: 2px;")
        self.progress_bar.move(100, self.height() - 40)
        self.progress_bar.setFixedWidth(0)
        
        # Set appropriate z-order of elements
        self.movie_label.lower()  # Background at the very back
        self.overlay.raise_()      # Overlay above background
        self.text_label.raise_()   # Text above overlay
        self.content_container.raise_()  # Content above text
        self.progress_bar.raise_() # Progress bar on top
        
        # Set up the loading animation - do it immediately in init
        self.movie = None  # Initialize to None for safety
        self.load_animation()
        
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

    def load_animation(self):
        """Load the splash screen animation"""
        # Check multiple potential paths for the splash screen GIF
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "resources", "splash_screen.gif"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "splash_screen.gif"),
            os.path.join(os.path.dirname(__file__), "splash_screen.gif"),
            os.path.abspath("sqlshell/resources/splash_screen.gif"),
            os.path.abspath("resources/splash_screen.gif")
        ]
        
        # Try each possible path
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Loading splash screen animation from: {path}")
                try:
                    self.movie = QMovie(path)
                    self.movie.setCacheMode(QMovie.CacheMode.CacheAll)  # Cache all frames for smoother playback
                    self.movie.setScaledSize(self.size())
                    
                    # Connect frameChanged signal to update the label
                    self.movie.frameChanged.connect(self.update_frame)
                    
                    # Ensure the movie label is visible and on top
                    self.movie_label.raise_()
                    self.movie_label.setStyleSheet("background: transparent;")
                    
                    # Set the movie to the label
                    self.movie_label.setMovie(self.movie)
                    
                    # Test if the movie is valid
                    if self.movie.isValid():
                        print(f"Successfully loaded animation with {self.movie.frameCount()} frames")
                        self.use_fallback = False
                        
                        # Create a timer to ensure animation updates
                        self.animation_timer = QTimer(self)
                        self.animation_timer.timeout.connect(self.update_animation)
                        self.animation_timer.start(50)  # Update every 50ms
                        
                        return
                    else:
                        print(f"Warning: Animation file at {path} is not valid")
                        self.use_fallback = True
                except Exception as e:
                    print(f"Error loading animation from {path}: {e}")
        
        # If we get here, no valid animation was found
        print("No valid animation found, using fallback static splash screen")
        self.use_fallback = True

    def update_frame(self):
        """Handle frame changed in the animation"""
        # Make sure the movie label is refreshed and visible
        self.movie_label.update()
        self.movie_label.show()
        self.movie_label.raise_()  # Ensure it stays on top
        
    def update_animation(self):
        """Ensure animation keeps running"""
        if self.movie and not self.use_fallback:
            # Check if movie is running
            if self.movie.state() != QMovie.MovieState.Running:
                self.movie.start()
            
            # Force update of the movie label
            self.movie_label.update()

    def paintEvent(self, event):
        """Custom paint event to draw a fallback splash screen if needed"""
        if self.use_fallback:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw rounded rectangle background
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(44, 62, 80))   # Dark blue-gray
            gradient.setColorAt(1, QColor(52, 152, 219)) # Bright blue
            
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
            
            # Draw progress bar
            if hasattr(self, '_progress'):
                progress_width = int(200 * self._progress)
                progress_rect = QRect(100, self.height() - 40, progress_width, 4)
                painter.setBrush(QColor(26, 188, 156))  # Teal
                painter.drawRoundedRect(progress_rect, 2, 2)
        
        super().paintEvent(event)

    def start_animations(self):
        """Start all animations"""
        # Try to start the movie if we have one
        if self.movie and not self.use_fallback:
            self.movie.start()
            
            # Check if movie is running after attempt to start
            if not self.movie.state() == QMovie.MovieState.Running:
                print("Warning: Could not start the animation")
                self.use_fallback = True
            else:
                # Ensure the movie label is visible and updated
                self.movie_label.show()
                self.movie_label.update()
                
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
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setFixedWidth(int(200 * value))
        # Force repaint if using fallback
        if self.use_fallback:
            self.update()

    def _on_animation_finished(self):
        """Handle animation completion"""
        if self.next_widget:
            QTimer.singleShot(500, self._finish_splash)

    def _finish_splash(self):
        """Clean up and show the main window"""
        # Stop the animation timer if it exists
        if hasattr(self, 'animation_timer') and self.animation_timer:
            self.animation_timer.stop()
            
        if self.movie:
            self.movie.stop()
        if self.fade_anim:
            self.fade_anim.stop()
        if self.progress_anim:
            self.progress_anim.stop()
        self.close()
        if self.next_widget:
            self.next_widget.show()

    def finish(self, widget):
        """Store the widget to show after animation completes"""
        self.next_widget = widget 