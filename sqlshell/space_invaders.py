"""
Space Invaders mini-game for SQLShell About menu.
A classic arcade game implemented in PyQt6.
"""

import random
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QDialog
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QKeyEvent


class SpaceInvadersGame(QWidget):
    """The main Space Invaders game widget."""
    
    game_over_signal = pyqtSignal(int)  # Signal emitted with final score
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(500, 600)
        
        # Game state
        self.game_running = False
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.level = 1
        
        # Player
        self.player_x = 250
        self.player_width = 50
        self.player_height = 20
        self.player_speed = 8
        
        # Bullets
        self.bullets = []
        self.bullet_speed = 10
        self.can_shoot = True
        self.shoot_cooldown = 250  # ms
        
        # Invaders
        self.invaders = []
        self.invader_direction = 1
        self.invader_speed = 2
        self.invader_drop = 20
        self.invader_width = 35
        self.invader_height = 25
        
        # Invader bullets
        self.invader_bullets = []
        self.invader_bullet_speed = 5
        
        # Stars background
        self.stars = [(random.randint(0, 500), random.randint(0, 600)) for _ in range(100)]
        
        # Colors - retro arcade style
        self.bg_color = QColor(5, 5, 20)
        self.player_color = QColor(0, 255, 100)
        self.bullet_color = QColor(255, 255, 0)
        self.invader_colors = [
            QColor(255, 50, 50),    # Red
            QColor(255, 150, 50),   # Orange
            QColor(255, 255, 50),   # Yellow
            QColor(50, 255, 255),   # Cyan
        ]
        self.star_color = QColor(255, 255, 255, 100)
        
        # Timers
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.game_loop)
        
        self.shoot_timer = QTimer(self)
        self.shoot_timer.timeout.connect(self.enable_shooting)
        self.shoot_timer.setSingleShot(True)
        
        self.invader_shoot_timer = QTimer(self)
        self.invader_shoot_timer.timeout.connect(self.invader_shoot)
        
        # Key states
        self.keys_pressed = set()
        
        # Initialize game
        self.init_invaders()
    
    def init_invaders(self):
        """Initialize the invader grid."""
        self.invaders = []
        rows = min(4, 2 + self.level // 2)
        cols = min(10, 6 + self.level // 2)
        
        start_x = (500 - cols * 45) // 2
        start_y = 60
        
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * 45
                y = start_y + row * 35
                color_idx = row % len(self.invader_colors)
                self.invaders.append({
                    'x': x,
                    'y': y,
                    'color': self.invader_colors[color_idx],
                    'alive': True
                })
    
    def start_game(self):
        """Start the game."""
        self.game_running = True
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.level = 1
        self.player_x = 225
        self.bullets = []
        self.invader_bullets = []
        self.invader_direction = 1
        self.invader_speed = 2
        self.init_invaders()
        
        self.game_timer.start(16)  # ~60 FPS
        self.invader_shoot_timer.start(1500)
        self.setFocus()
    
    def stop_game(self):
        """Stop the game."""
        self.game_running = False
        self.game_timer.stop()
        self.invader_shoot_timer.stop()
    
    def game_loop(self):
        """Main game loop."""
        if not self.game_running:
            return
        
        self.handle_input()
        self.update_bullets()
        self.update_invaders()
        self.update_invader_bullets()
        self.check_collisions()
        self.check_level_complete()
        
        self.update()
    
    def handle_input(self):
        """Handle player input."""
        if Qt.Key.Key_Left in self.keys_pressed or Qt.Key.Key_A in self.keys_pressed:
            self.player_x = max(0, self.player_x - self.player_speed)
        if Qt.Key.Key_Right in self.keys_pressed or Qt.Key.Key_D in self.keys_pressed:
            self.player_x = min(500 - self.player_width, self.player_x + self.player_speed)
        if Qt.Key.Key_Space in self.keys_pressed and self.can_shoot:
            self.shoot()
    
    def shoot(self):
        """Fire a bullet."""
        if not self.can_shoot:
            return
        
        bullet_x = self.player_x + self.player_width // 2 - 2
        bullet_y = 560
        self.bullets.append({'x': bullet_x, 'y': bullet_y})
        
        self.can_shoot = False
        self.shoot_timer.start(self.shoot_cooldown)
    
    def enable_shooting(self):
        """Re-enable shooting after cooldown."""
        self.can_shoot = True
    
    def invader_shoot(self):
        """Random invader shoots."""
        if not self.game_running:
            return
        
        alive_invaders = [inv for inv in self.invaders if inv['alive']]
        if alive_invaders:
            shooter = random.choice(alive_invaders)
            self.invader_bullets.append({
                'x': shooter['x'] + self.invader_width // 2,
                'y': shooter['y'] + self.invader_height
            })
    
    def update_bullets(self):
        """Update player bullet positions."""
        for bullet in self.bullets[:]:
            bullet['y'] -= self.bullet_speed
            if bullet['y'] < 0:
                self.bullets.remove(bullet)
    
    def update_invader_bullets(self):
        """Update invader bullet positions."""
        for bullet in self.invader_bullets[:]:
            bullet['y'] += self.invader_bullet_speed
            if bullet['y'] > 600:
                self.invader_bullets.remove(bullet)
    
    def update_invaders(self):
        """Update invader positions."""
        alive_invaders = [inv for inv in self.invaders if inv['alive']]
        if not alive_invaders:
            return
        
        # Check if any invader hits the edge
        hit_edge = False
        for inv in alive_invaders:
            if self.invader_direction > 0 and inv['x'] + self.invader_width >= 490:
                hit_edge = True
                break
            elif self.invader_direction < 0 and inv['x'] <= 10:
                hit_edge = True
                break
        
        if hit_edge:
            self.invader_direction *= -1
            for inv in alive_invaders:
                inv['y'] += self.invader_drop
        else:
            for inv in alive_invaders:
                inv['x'] += self.invader_speed * self.invader_direction
    
    def check_collisions(self):
        """Check for collisions."""
        # Player bullets vs invaders
        for bullet in self.bullets[:]:
            bullet_rect = QRectF(bullet['x'], bullet['y'], 4, 10)
            for inv in self.invaders:
                if not inv['alive']:
                    continue
                inv_rect = QRectF(inv['x'], inv['y'], self.invader_width, self.invader_height)
                if bullet_rect.intersects(inv_rect):
                    inv['alive'] = False
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    self.score += 10 * self.level
                    break
        
        # Invader bullets vs player
        player_rect = QRectF(self.player_x, 560, self.player_width, self.player_height)
        for bullet in self.invader_bullets[:]:
            bullet_rect = QRectF(bullet['x'], bullet['y'], 4, 10)
            if bullet_rect.intersects(player_rect):
                self.invader_bullets.remove(bullet)
                self.lives -= 1
                if self.lives <= 0:
                    self.end_game()
        
        # Check if invaders reached the player
        for inv in self.invaders:
            if inv['alive'] and inv['y'] + self.invader_height >= 540:
                self.end_game()
                break
    
    def check_level_complete(self):
        """Check if all invaders are destroyed."""
        alive_invaders = [inv for inv in self.invaders if inv['alive']]
        if not alive_invaders:
            self.level += 1
            self.invader_speed = min(6, 2 + self.level * 0.5)
            self.init_invaders()
            self.invader_bullets = []
            # Bonus points for completing level
            self.score += 100 * self.level
    
    def end_game(self):
        """End the game."""
        self.game_over = True
        self.stop_game()
        self.game_over_signal.emit(self.score)
        self.update()
    
    def paintEvent(self, event):
        """Render the game."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Stars
        painter.setPen(QPen(self.star_color))
        for star in self.stars:
            painter.drawPoint(star[0], star[1])
        
        if not self.game_running and not self.game_over:
            self.draw_start_screen(painter)
            return
        
        # Draw player
        painter.setBrush(QBrush(self.player_color))
        painter.setPen(Qt.PenStyle.NoPen)
        # Ship body
        painter.drawRect(int(self.player_x), 565, self.player_width, 15)
        # Ship cockpit
        painter.drawRect(int(self.player_x) + 20, 555, 10, 10)
        
        # Draw player bullets
        painter.setBrush(QBrush(self.bullet_color))
        for bullet in self.bullets:
            painter.drawRect(int(bullet['x']), int(bullet['y']), 4, 10)
        
        # Draw invaders
        for inv in self.invaders:
            if not inv['alive']:
                continue
            painter.setBrush(QBrush(inv['color']))
            # Invader body
            self.draw_invader(painter, int(inv['x']), int(inv['y']))
        
        # Draw invader bullets
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        for bullet in self.invader_bullets:
            painter.drawRect(int(bullet['x']), int(bullet['y']), 4, 10)
        
        # Draw UI
        self.draw_ui(painter)
        
        if self.game_over:
            self.draw_game_over(painter)
    
    def draw_invader(self, painter, x, y):
        """Draw a pixelated invader."""
        # Main body
        painter.drawRect(x + 5, y + 5, 25, 15)
        # Antennae
        painter.drawRect(x + 2, y, 6, 8)
        painter.drawRect(x + 27, y, 6, 8)
        # Eyes
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawRect(x + 10, y + 8, 5, 5)
        painter.drawRect(x + 20, y + 8, 5, 5)
        # Restore color
        painter.setBrush(QBrush(self.invader_colors[0]))
    
    def draw_ui(self, painter):
        """Draw score and lives."""
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont('Courier', 14, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Score
        painter.drawText(10, 25, f'SCORE: {self.score}')
        
        # Level
        painter.drawText(200, 25, f'LEVEL: {self.level}')
        
        # Lives
        painter.drawText(380, 25, f'LIVES: {"♥" * self.lives}')
    
    def draw_start_screen(self, painter):
        """Draw the start screen."""
        painter.setPen(QPen(QColor(0, 255, 100)))
        
        # Title
        title_font = QFont('Courier', 32, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, 
                        '\n\nSPACE INVADERS')
        
        # SQLShell edition
        sub_font = QFont('Courier', 14)
        painter.setFont(sub_font)
        painter.setPen(QPen(QColor(100, 200, 255)))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignHCenter, 
                        '\n\n\n\n\n\nSQLShell Edition')
        
        # Instructions
        painter.setPen(QPen(QColor(255, 255, 255)))
        inst_font = QFont('Courier', 12)
        painter.setFont(inst_font)
        
        instructions = [
            '',
            '',
            '← → or A D: Move',
            'SPACE: Shoot',
            '',
            'Press SPACE or click START to play!'
        ]
        
        y = 300
        for line in instructions:
            painter.drawText(self.rect().adjusted(0, y, 0, 0), 
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, line)
            y += 25
        
        # Draw sample invaders
        painter.setBrush(QBrush(self.invader_colors[0]))
        self.draw_invader(painter, 150, 200)
        painter.setBrush(QBrush(self.invader_colors[1]))
        self.draw_invader(painter, 220, 200)
        painter.setBrush(QBrush(self.invader_colors[2]))
        self.draw_invader(painter, 290, 200)
    
    def draw_game_over(self, painter):
        """Draw game over screen."""
        # Darken background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        
        painter.setPen(QPen(QColor(255, 50, 50)))
        font = QFont('Courier', 36, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'GAME OVER')
        
        painter.setPen(QPen(QColor(255, 255, 255)))
        score_font = QFont('Courier', 18)
        painter.setFont(score_font)
        painter.drawText(self.rect().adjusted(0, 60, 0, 0), 
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter,
                        f'Final Score: {self.score}')
        
        painter.setPen(QPen(QColor(100, 255, 100)))
        painter.drawText(self.rect().adjusted(0, 120, 0, 0), 
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter,
                        'Press SPACE to play again')
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press."""
        self.keys_pressed.add(event.key())
        
        if event.key() == Qt.Key.Key_Space:
            if not self.game_running:
                self.start_game()
        
        event.accept()
    
    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release."""
        self.keys_pressed.discard(event.key())
        event.accept()


class SpaceInvadersDialog(QDialog):
    """Dialog wrapper for the Space Invaders game."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🎮 Space Invaders - SQLShell Edition')
        self.setMinimumSize(520, 700)
        self.setModal(True)
        
        # Dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a1a;
            }
            QPushButton {
                background-color: #1a3a1a;
                color: #00ff64;
                border: 2px solid #00ff64;
                padding: 10px 20px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a5a2a;
            }
            QPushButton:pressed {
                background-color: #0a2a0a;
            }
            QLabel {
                color: #00ff64;
                font-family: 'Courier New', monospace;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Game widget
        self.game = SpaceInvadersGame(self)
        layout.addWidget(self.game)
        
        # Start button
        self.start_btn = QPushButton('▶ START GAME')
        self.start_btn.clicked.connect(self.start_game)
        layout.addWidget(self.start_btn)
        
        # Close button
        self.close_btn = QPushButton('✕ CLOSE')
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
    
    def start_game(self):
        """Start the game."""
        self.game.start_game()
        self.start_btn.setText('▶ RESTART')
    
    def keyPressEvent(self, event: QKeyEvent):
        """Forward key events to game."""
        self.game.keyPressEvent(event)
    
    def keyReleaseEvent(self, event: QKeyEvent):
        """Forward key events to game."""
        self.game.keyReleaseEvent(event)


def show_space_invaders(parent=None):
    """Show the Space Invaders game dialog."""
    dialog = SpaceInvadersDialog(parent)
    dialog.exec()

