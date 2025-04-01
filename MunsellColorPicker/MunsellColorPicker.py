import math
from .MunsellFloats import *
from krita import *
from krita import ManagedColor
from PyQt5.QtCore import QSize, QTimer, Qt
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QApplication, QColorDialog, QGridLayout
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QClipboard

DOCKER_TITLE = 'Munsell Color Picker'

class ClickableLabel(QLabel):
    """Custom QLabel that copies text to clipboard on click and updates FG color"""
    colorClicked = pyqtSignal(str)  # Signal for color selection

    def __init__(self, text, color_hex):
        super().__init__(text)
        self.color_hex = color_hex
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self.getStyleSheet(color_hex))
        self.setAlignment(Qt.AlignCenter)

    def getStyleSheet(self, color_hex):
        """Adjust text color for visibility"""
        r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
        text_color = "#FFFFFF" if (r * 0.299 + g * 0.587 + b * 0.114) < 128 else "#000000"
        return f"background-color: {color_hex}; color: {text_color}; padding: 5px; border-radius: 4px;"

    def setTextAndColor(self, text, color_hex):
        """Update text and background color dynamically"""
        self.color_hex = color_hex
        self.setText(text)
        self.setStyleSheet(self.getStyleSheet(color_hex))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.color_hex)  # Copy hex to clipboard
            self.colorClicked.emit(self.color_hex)  # Emit signal when clicked
class DockerTemplate(DockWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(DOCKER_TITLE)

        self.error_clear_timer = QTimer()
        self.error_clear_timer.setSingleShot(True)
        self.error_clear_timer.timeout.connect(self.clearErrorMessage)

        self.colorUpdateTimer = QTimer()
        self.colorUpdateTimer.timeout.connect(self.updateColorInfo)
        self.colorUpdateTimer.start(500)

        self.setUI()
        self.last_foreground_hex = None

    def setUI(self):
        self.base_widget = QWidget()
        self.main_container = QVBoxLayout()
        self.main_container.setContentsMargins(1, 1, 1, 1)

        color_layout = QHBoxLayout()

        # Foreground Hex Text (Copies Hex)
        self.fg_color_label = ClickableLabel("#000000", "#000000")
        color_layout.addWidget(self.fg_color_label)

        # Foreground Color Button (Opens Color Picker)
        self.fg_color_button = QPushButton()
        self.fg_color_button.setFixedSize(40, 20)
        self.fg_color_button.clicked.connect(self.onFgColorClick)
        color_layout.addWidget(self.fg_color_button)

        # Background Hex Text (Copies Hex)
        self.bg_color_label = ClickableLabel("#000000", "#000000")
        color_layout.addWidget(self.bg_color_label)

        # Background Color Button (Opens Color Picker)
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(40, 20)
        self.bg_color_button.clicked.connect(self.onBgColorClick)
        color_layout.addWidget(self.bg_color_button)

        self.main_container.addLayout(color_layout)

        # Grid for transition colors
        self.color_grid = QGridLayout()
        self.main_container.addLayout(self.color_grid)

        # Grid for Munsell colors
        self.munsell_grid = QGridLayout()
        self.main_container.addLayout(self.munsell_grid)

        # History layout
        self.color_history = []  # list of hex strings
        self.color_history_grid = QGridLayout()
        self.main_container.addLayout(self.color_history_grid)

        # Exception display box
        self.error_display = QLabel("")
        self.error_display.setStyleSheet("color: red;")
        self.main_container.addWidget(self.error_display)

        self.base_widget.setLayout(self.main_container)
        self.setWidget(self.base_widget)

        self.base_widget.setMinimumSize(QSize(250, 150))

        self.updateColorInfo()
        
    def updateColorInfo(self):
        """Update the color information and generate transition colors"""
        try:
            if Krita.instance():
                view = Application.activeWindow().activeView()
                fg_color = view.foregroundColor()
                bg_color = view.backgroundColor()

                fg_components = fg_color.components()
                bg_components = bg_color.components()

                fg_r, fg_g, fg_b = [int(fg_components[i] * 255) for i in [2, 1, 0]]
                bg_r, bg_g, bg_b = [int(bg_components[i] * 255) for i in [2, 1, 0]]

                fg_hex = f"#{fg_r:02X}{fg_g:02X}{fg_b:02X}"
                bg_hex = f"#{bg_r:02X}{bg_g:02X}{bg_b:02X}"

                self.fg_color_label.setTextAndColor(fg_hex, fg_hex)
                self.bg_color_label.setTextAndColor(bg_hex, bg_hex)

                self.fg_color_button.setStyleSheet(f"background-color: {fg_hex};")
                self.bg_color_button.setStyleSheet(f"background-color: {bg_hex};")

                # Clear the grid before adding new labels
                for i in reversed(range(self.color_grid.count())):
                    self.color_grid.itemAt(i).widget().setParent(None)

                # Generate 10 gradient transition colors
                for i in range(10):
                    ratio = i / 9.0  # Normalize between 0 and 1
                    mid_r = int(fg_r * (1 - ratio) + bg_r * ratio)
                    mid_g = int(fg_g * (1 - ratio) + bg_g * ratio)
                    mid_b = int(fg_b * (1 - ratio) + bg_b * ratio)

                    mid_hex = f"#{mid_r:02X}{mid_g:02X}{mid_b:02X}"

                    # Place in 2 rows of 5
                    row, col = divmod(i, 5)

                    label = ClickableLabel(mid_hex, mid_hex)
                    label.colorClicked.connect(self.setForeGroundColor)  # Connect click event
                    self.color_grid.addWidget(label, row, col)
                
                # Add another grid of Munsell-based interpolated colors
                if hasattr(self, 'munsell_grid'):
                    for i in reversed(range(self.munsell_grid.count())):
                        self.munsell_grid.itemAt(i).widget().setParent(None)
                else:
                    self.munsell_grid = QGridLayout()
                    self.main_container.addLayout(self.munsell_grid)

                # Derive value/chroma inputs from foreground color
                fg_luma = 0.299 * fg_r + 0.587 * fg_g + 0.114 * fg_b  # approximate lightness
                fg_luma_norm = fg_luma / 255

                # Use lightness to affect Munsell j_pos and k_pos
                for i in range(10):
                    i_pos = (i % 5) / 5 * 39                      # hue
                    j_pos = 0.1 + fg_luma_norm * 0.9              # value
                    k_pos = 0.5 + ((i // 5) / 1.0) * 1.5           # chroma
                    j_pos = max(0, min(1, j_pos))
                    k_pos = max(0, min(1, k_pos))
                    rgb = munsell_interpolate(i_pos, j_pos, k_pos)
                    hex_code = "#{:02X}{:02X}{:02X}".format(*rgb)
                    label = ClickableLabel(hex_code, hex_code)
                    label.colorClicked.connect(self.setForeGroundColor)
                    self.munsell_grid.addWidget(label, i // 5, i % 5)

            if self.last_foreground_hex != fg_hex:
                self.addColorToHistory(fg_hex)
                self.last_foreground_hex = fg_hex
                
        except Exception as e:
            self.showError(f"Update Error: {str(e)}")
            
    def showError(self, message):
        """Display error and start a timer to clear it after 5 seconds"""
        self.error_display.setText(message)
        self.error_clear_timer.start(5000)

    def clearErrorMessage(self):
        """Clear the error display box"""
        self.error_display.clear()

    def canvasChanged(self, canvas):
        if canvas:
            self.updateColorInfo()

    def onFgColorClick(self):
        """Open color picker when foreground button is clicked"""
        try:
            color = QColorDialog.getColor()
            if color.isValid():
                view = Krita.instance().activeWindow().activeView()
                if view:
                    managed = ManagedColor("RGBA", "U8", "")
                    components = managed.components()
                    components[2] = color.redF()
                    components[1] = color.greenF()
                    components[0] = color.blueF()
                    components[3] = 1.0
                    managed.setComponents(components)
                    view.setForeGroundColor(managed)
                    self.updateColorInfo()
                    
                    hex_code = "#{:02X}{:02X}{:02X}".format(color.red(), color.green(), color.blue())
                    self.addColorToHistory(hex_code)
        except Exception as e:
            self.showError(f"FG Error: {str(e)}")


    def onBgColorClick(self):
        """Open color picker when background button is clicked"""
        try:
            color = QColorDialog.getColor()
            if color.isValid():
                view = Krita.instance().activeWindow().activeView()
                if view:
                    managed = ManagedColor("RGBA", "U8", "")
                    components = managed.components()
                    components[2] = color.redF()
                    components[1] = color.greenF()
                    components[0] = color.blueF()
                    components[3] = 1.0
                    managed.setComponents(components)
                    view.setBackgroundColor(managed)
                    self.updateColorInfo()
                    
                    hex_code = "#{:02X}{:02X}{:02X}".format(color.red(), color.green(), color.blue())
                    self.addColorToHistory(hex_code)
        except Exception as e:
            self.showError(f"BG Error: {str(e)}")
            
    def setForeGroundColor(self, color_hex):
        """Set the clicked color as the new foreground color using ManagedColor"""
        try:
            view = Krita.instance().activeWindow().activeView()
            if view:
                color = ManagedColor("RGBA", "U8", "")
                r = int(color_hex[1:3], 16) / 255
                g = int(color_hex[3:5], 16) / 255
                b = int(color_hex[5:7], 16) / 255
                components = color.components()
                components[2] = r
                components[1] = g
                components[0] = b
                components[3] = 1.0  # alpha
                color.setComponents(components)
                view.setForeGroundColor(color)
                self.updateColorInfo()
                self.addColorToHistory(color_hex)

        except Exception as e:
            self.showError(f"FG Set Error: {str(e)}")
            
    def addColorToHistory(self, hex_code):
        # Remove if already in history
        if hex_code in self.color_history:
            self.color_history.remove(hex_code)

        # Append to end
        self.color_history.append(hex_code)

        # Limit size
        if len(self.color_history) > 10:
            self.color_history.pop(0)

        # Rebuild the grid
        for i in reversed(range(self.color_history_grid.count())):
            self.color_history_grid.itemAt(i).widget().setParent(None)
        for idx, hex_code in enumerate(self.color_history):
            row, col = divmod(idx, 5)
            label = ClickableLabel(hex_code, hex_code)
            label.colorClicked.connect(self.setForeGroundColor)
            self.color_history_grid.addWidget(label, row, col)


def mul(factor, maybe_number):
    if factor == 0 or maybe_number is None or math.isnan(maybe_number):
        return 0
    return factor * maybe_number

def munsell_interpolate(i, j, k):
    i0 = int(math.floor(i))
    j0 = int(math.floor(j))
    k0 = int(math.floor(k))
    i1 = (i0 + 1) % 40
    j1 = j0 + 1
    k1 = k0 + 1
    a1 = i - i0
    b1 = j - j0
    c1 = k - k0
    a0 = 1 - a1
    b0 = 1 - b1
    c0 = 1 - c1
    ans = [0.0, 0.0, 0.0]
    for t in range(3):
        ans[t] = (
            mul(a0 * b0 * c0, Munsell[i0][j0][k0][t]) +
            mul(a1 * b0 * c0, Munsell[i1][j0][k0][t]) +
            mul(a0 * b1 * c0, Munsell[i0][j1][k0][t]) +
            mul(a1 * b1 * c0, Munsell[i1][j1][k0][t]) +
            mul(a0 * b0 * c1, Munsell[i0][j0][k1][t]) +
            mul(a1 * b0 * c1, Munsell[i1][j0][k1][t]) +
            mul(a0 * b1 * c1, Munsell[i0][j1][k1][t]) +
            mul(a1 * b1 * c1, Munsell[i1][j1][k1][t])
        )
    return [int(max(0, min(255, round(v * 255)))) for v in ans]
