from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor

class BarChartDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_val = 0
        self.max_val = 1
        self.bar_color = QColor("#3498DB")

    def set_range(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val

    def paint(self, painter, option, index):
        # Draw the default background
        super().paint(painter, option, index)
        
        try:
            text = index.data()
            value = float(text.replace(',', ''))
            
            # Calculate normalized value
            range_val = self.max_val - self.min_val if self.max_val != self.min_val else 1
            normalized = (value - self.min_val) / range_val
            
            # Define bar dimensions
            bar_height = 16
            max_bar_width = 100
            bar_width = max(5, int(max_bar_width * normalized))
            
            # Calculate positions
            text_width = option.fontMetrics.horizontalAdvance(text) + 10
            bar_x = option.rect.left() + text_width + 10
            bar_y = option.rect.center().y() - bar_height // 2
            
            # Draw the bar
            bar_rect = QRect(bar_x, bar_y, bar_width, bar_height)
            painter.fillRect(bar_rect, self.bar_color)
            
            # Draw the text
            text_rect = QRect(option.rect.left() + 4, option.rect.top(),
                            text_width, option.rect.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            
        except (ValueError, AttributeError):
            # If not a number, just draw the text
            super().paint(painter, option, index) 