import math
import os
from .MunsellInterpolate import *
from krita import * # type: ignore
from krita import ManagedColor # type: ignore
from PyQt5.QtCore import QSize, QTimer, Qt
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QApplication, QColorDialog, QGridLayout, QTextEdit, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QClipboard, QTextCursor
import colorsys

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

class DockerTemplate(DockWidget): # type: ignore

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

    def setUI(self):
        self.last_foreground_hex = None
        self.cached_light_chroma_colors = []
        self.cached_hue_chroma_colors = []
        self.cached_light_hue_colors = []
        
        self.base_widget = QWidget()
        self.main_container = QVBoxLayout()
        self.main_container.setContentsMargins(1, 1, 1, 1)

        color_layout = QHBoxLayout()
        color_layout.setSpacing(4)  # Reduce space between fg/bg labels and buttons
        color_layout.setContentsMargins(0, 0, 0, 0)  # Optional: remove outer padding

        # Radio buttons to switch grids
        self.mode_lightchroma = QRadioButton("Fixed Hue")
        self.mode_huechroma = QRadioButton("Fixed Light")
        self.mode_lighthue = QRadioButton("Fixed Chroma")
        self.mode_lightchroma.setChecked(True)

        mode_buttons = QHBoxLayout()
        mode_buttons.addWidget(self.mode_lightchroma)
        mode_buttons.addWidget(self.mode_huechroma)
        mode_buttons.addWidget(self.mode_lighthue)
        self.main_container.addLayout(mode_buttons)

        # Group them to manage logic
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.addButton(self.mode_lightchroma)
        self.mode_button_group.addButton(self.mode_huechroma)
        self.mode_button_group.addButton(self.mode_lighthue)
        self.mode_lightchroma.toggled.connect(self.updateModeVisibility)
        self.mode_huechroma.toggled.connect(self.updateModeVisibility)
        self.mode_lighthue.toggled.connect(self.updateModeVisibility)

        # Generate Light-Chroma button (next to radio)
        self.generate_lightchroma_button = QPushButton("Generate")
        self.generate_lightchroma_button.clicked.connect(self.onGenerateLightChroma)
        mode_buttons.addWidget(self.generate_lightchroma_button)
        
        # Generate Hue-Chroma button (next to radio)
        self.generate_huechroma_button = QPushButton("Generate")
        self.generate_huechroma_button.clicked.connect(self.onGenerateHueChroma)
        mode_buttons.addWidget(self.generate_huechroma_button)
        
        # Generate Light–Hue button
        self.generate_lighthue_button = QPushButton("Generate")
        self.generate_lighthue_button.clicked.connect(self.onGenerateLightHue)
        mode_buttons.addWidget(self.generate_lighthue_button)

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
        transition_header = QLabel("Color Transition")
        transition_header.setStyleSheet("font-weight: bold; margin-top: 6px;")
        self.main_container.addWidget(transition_header)
        self.color_grid = QGridLayout()
        self.main_container.addLayout(self.color_grid)

        grid_header = QLabel("Color Grid")
        grid_header.setStyleSheet("font-weight: bold; margin-top: 6px;")
        self.main_container.addWidget(grid_header)
        
        # Grid for Hue-Chroma colors
        self.lightchroma_grid = QGridLayout()
        self.lightchroma_grid.setSpacing(1)
        self.lightchroma_grid.setContentsMargins(0, 0, 0, 0)
        self.main_container.addLayout(self.lightchroma_grid)

        # Grid for Hue-Chroma colors
        self.huechroma_grid = QGridLayout()
        self.huechroma_grid.setSpacing(1)
        self.huechroma_grid.setContentsMargins(0, 0, 0, 0)
        self.main_container.addLayout(self.huechroma_grid)

        # Grid for Light–Hue colors
        self.lighthue_grid = QGridLayout()
        self.lighthue_grid.setSpacing(1)
        self.lighthue_grid.setContentsMargins(0, 0, 0, 0)
        self.main_container.addLayout(self.lighthue_grid)

        # History layout
        history_header = QLabel("Color History")
        history_header.setStyleSheet("font-weight: bold; margin-top: 6px;")
        self.main_container.addWidget(history_header)
        self.color_history = []  # list of hex strings
        self.color_history_grid = QGridLayout()
        self.main_container.addLayout(self.color_history_grid)

        # Exception display box (disappears after 5s)
        self.error_display = QLabel("")
        self.error_display.setStyleSheet("color: red;")
        self.main_container.addWidget(self.error_display)

        self.base_widget.setLayout(self.main_container)
        self.setWidget(self.base_widget)

        self.base_widget.setMinimumSize(QSize(250, 150))

        self.updateColorInfo()
        self.updateModeVisibility()
        
    def updateModeVisibility(self):
        is_lightchroma = self.mode_lightchroma.isChecked()
        is_huechroma = self.mode_huechroma.isChecked()
        is_lighthue = self.mode_lighthue.isChecked()

        # Toggle button visibility
        self.generate_lightchroma_button.setVisible(is_lightchroma)
        self.generate_huechroma_button.setVisible(is_huechroma)
        self.generate_lighthue_button.setVisible(is_lighthue)

        # Clear all visible grid widgets (but keep layout structure)
        self.setLayoutVisibility(self.lightchroma_grid, False)
        self.setLayoutVisibility(self.huechroma_grid, False)
        self.setLayoutVisibility(self.lighthue_grid, False)

        # Show the one relevant layout
        if is_lightchroma:
            if not self.cached_light_chroma_colors:
                self.onGenerateLightChroma()
            else:
                self.renderLightChromaGrid()
            self.setLayoutVisibility(self.lightchroma_grid, True)

        elif is_huechroma:
            if not self.cached_hue_chroma_colors:
                self.onGenerateHueChroma()
            else:
                self.renderHueChromaGrid()
            self.setLayoutVisibility(self.huechroma_grid, True)

        elif is_lighthue:
            if not self.cached_light_hue_colors:
                self.onGenerateLightHue()
            else:
                self.renderLightHueGrid()
            self.setLayoutVisibility(self.lighthue_grid, True)

    def setLayoutVisibility(self, layout, visible):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(visible)
            
    def updateColorInfo(self):
        """Update the color information and generate transition colors"""
        try:
            if Krita.instance(): # type: ignore
                view = Krita.instance().activeWindow().activeView() # type: ignore
                fg_color = view.foregroundColor()
                bg_color = view.backgroundColor()

                fg_components = fg_color.components()
                bg_components = bg_color.components()

                fg_r, fg_g, fg_b = [int(fg_components[i] * 255) for i in [2, 1, 0]]
                bg_r, bg_g, bg_b = [int(bg_components[i] * 255) for i in [2, 1, 0]]

                fg_hex = f"#{fg_r:02X}{fg_g:02X}{fg_b:02X}"
                bg_hex = f"#{bg_r:02X}{bg_g:02X}{bg_b:02X}"

                if self.last_foreground_hex != fg_hex:
                    # update only if color changed
                    self.fg_color_label.setTextAndColor(fg_hex, fg_hex)
                    self.bg_color_label.setTextAndColor(bg_hex, bg_hex)

                    self.fg_color_button.setStyleSheet(f"background-color: {fg_hex};")
                    self.bg_color_button.setStyleSheet(f"background-color: {bg_hex};")

                    # Update transition colors
                    for i in reversed(range(self.color_grid.count())):
                        self.color_grid.itemAt(i).widget().setParent(None)

                    for i in range(10):
                        ratio = i / 9.0
                        mid_r = int(fg_r * (1 - ratio) + bg_r * ratio)
                        mid_g = int(fg_g * (1 - ratio) + bg_g * ratio)
                        mid_b = int(fg_b * (1 - ratio) + bg_b * ratio)
                        mid_hex = f"#{mid_r:02X}{mid_g:02X}{mid_b:02X}"
                        row, col = divmod(i, 5)
                        label = ClickableLabel(mid_hex, mid_hex)
                        label.colorClicked.connect(self.setForeGroundColor)
                        self.color_grid.addWidget(label, row, col)

                    self.last_foreground_hex = fg_hex

                    self.addColorToHistory(fg_hex)
                
        except Exception as e:
            self.showError(f"Update Error: {str(e)}")
            
    def onGenerateLightChroma(self):
        try:
            view = Krita.instance().activeWindow().activeView() # type: ignore
            if not view:
                return

            fg_color = view.foregroundColor()
            fg_components = fg_color.components()
            r_norm = fg_components[2]
            g_norm = fg_components[1]
            b_norm = fg_components[0]

            # Use HLS to get the lightness
            hue_float, _, _ = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
            hue_scaled = hue_float * 40.0
            self.cached_light_chroma_colors = self.GetLightChromaColors(hue_scaled)
            
            self.renderLightChromaGrid()

        except Exception as e:
            self.showError(f"Light-Chroma Error: {str(e)}")

    def renderLightChromaGrid(self):
        self.clearAllGrids()
        for i in reversed(range(self.lightchroma_grid.count())):
            item = self.lightchroma_grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        # Add updated hue-chroma colors to grid
        for light_index, row in enumerate(self.cached_light_chroma_colors):
            for chroma_index, color in enumerate(row):
                r, g, b = srgb_coords(color)
                hex_code = f"#{r:02X}{g:02X}{b:02X}"
                label = ClickableLabel(None, hex_code)
                label.colorClicked.connect(self.setForeGroundColor)
                self.lightchroma_grid.addWidget(label, light_index, chroma_index)  # chroma = row, hue = column

    def GetLightChromaColors(self, hue):
        all_colors = []

        for j in range(1, 15):  # Lightness levels
            row_colors = []
            for k in range(26):  # Chroma steps
                color = munsell_interpolate(hue, j, k)

                # Stop if color is clearly invalid or black placeholder
                if not color_charted(color) or color == [0, 0, 0]:
                    break

                color_norm = [c / 255.0 for c in color]

                if not color_valid(color_norm):
                    break

                srgb = srgb_coords(color_norm)
                if sum(srgb) <= 30:  # very dark or clipped
                    break

                row_colors.append(color_norm)

            if row_colors:
                all_colors.append(row_colors)

        return all_colors
    
    def GetHueChromaColors(self, light):
        # this is filling a like circle not a list
        all_colors = []

        for i in range(40):  # Hues (0–39)
            hue_colors = []

            for k in range(26):  # Chroma
                color = munsell_interpolate(i, light, k)

                if not color_charted(color) or color == [0, 0, 0]:
                    break

                color_norm = [c / 255.0 for c in color]

                if not color_valid(color_norm):
                    break

                srgb = srgb_coords(color_norm)

                if sum(srgb) <= 30:
                    break

                hue_colors.append(color_norm)

            all_colors.append(hue_colors)

        return all_colors
    
    def GetLightHueColors(self, chroma):
        all_colors = []

        for j in range(1, 15):  # Lightness (Value)
            row_colors = []
            for i in range(40):  # Hue
                color = munsell_interpolate(i, j, chroma)

                if not color_charted(color) or color == [0, 0, 0]:
                    continue

                color_norm = [c / 255.0 for c in color]
                if not color_valid(color_norm):
                    break

                srgb = srgb_coords(color_norm)
                if sum(srgb) <= 30:
                    break

                row_colors.append(color_norm)
            all_colors.append(row_colors)

        return all_colors
    
    def onGenerateLightHue(self):
        try:
            view = Krita.instance().activeWindow().activeView() # type: ignore
            if not view:
                return

            fg_color = view.foregroundColor()
            fg_components = fg_color.components()
            r_norm = fg_components[2]
            g_norm = fg_components[1]
            b_norm = fg_components[0]

            # Use HLS to extract chroma proxy (based on saturation)
            h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
            # Clamp saturation to index range [0–25] for 26 discrete chroma steps
            # Then normalize index back to [0–1]
            chroma_index = min(int(s * 25), 25) / 25

            self.cached_light_hue_colors = self.GetLightHueColors(chroma_index)
            self.renderLightHueGrid()
        except Exception as e:
            self.showError(f"Light-Hue Error: {str(e)}")
            
    def renderLightHueGrid(self):
        self.clearAllGrids()
        for i in reversed(range(self.lighthue_grid.count())):
            item = self.lighthue_grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
                
        for lightness_index, row in enumerate(self.cached_light_hue_colors):
            for hue_index, color in enumerate(row):
                r, g, b = srgb_coords(color)
                hex_code = f"#{r:02X}{g:02X}{b:02X}"
                label = ClickableLabel(None, hex_code)
                label.colorClicked.connect(self.setForeGroundColor)
                self.lighthue_grid.addWidget(label, lightness_index, hue_index)

    def onGenerateHueChroma(self):
        try:
            view = Krita.instance().activeWindow().activeView() # type: ignore
            if not view:
                return

            fg_color = view.foregroundColor()
            fg_components = fg_color.components()
            r_norm = fg_components[2]
            g_norm = fg_components[1]
            b_norm = fg_components[0]

            # Use HLS to get the lightness
            _, _, light_float = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
            lightness_index = max(1, min(round(light_float * 10), 10))  # Clamp
            self.cached_hue_chroma_colors = self.GetHueChromaColors(lightness_index)

            self.renderHueChromaGrid()

        except Exception as e:
            self.showError(f"Hue-Chroma Error: {str(e)}")

    def renderHueChromaGrid(self):
        self.clearAllGrids()
        # Clear existing hue-chroma grid
        for i in reversed(range(self.huechroma_grid.count())):
            item = self.huechroma_grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        # Add updated hue-chroma colors to grid
        for hue_index, row in enumerate(self.cached_hue_chroma_colors):
            for chroma_index, color in enumerate(row):
                r, g, b = srgb_coords(color)
                hex_code = f"#{r:02X}{g:02X}{b:02X}"
                label = ClickableLabel(None, hex_code)
                label.colorClicked.connect(self.setForeGroundColor)
                self.huechroma_grid.addWidget(label, chroma_index, hue_index)

    def clearAllGrids(self):
        for layout in [self.lightchroma_grid, self.huechroma_grid, self.lighthue_grid]:
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item and item.widget():
                    item.widget().setParent(None)

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
        """Open color picker initialized with the current foreground color"""
        try:
            view = Krita.instance().activeWindow().activeView()  # type: ignore
            if not view:
                return

            fg_color = view.foregroundColor()
            components = fg_color.components()
            initial_color = QColor(
                int(components[2] * 255),
                int(components[1] * 255),
                int(components[0] * 255),
            )

            color = QColorDialog.getColor(initial=initial_color)
            if color.isValid():
                managed = ManagedColor("RGBA", "U8", "")
                comps = managed.components()
                comps[2] = color.redF()
                comps[1] = color.greenF()
                comps[0] = color.blueF()
                comps[3] = 1.0
                managed.setComponents(comps)
                view.setForeGroundColor(managed)
                self.updateColorInfo()

                hex_code = "#{:02X}{:02X}{:02X}".format(color.red(), color.green(), color.blue())
                self.addColorToHistory(hex_code)

        except Exception as e:
            self.showError(f"FG Picker Error: {str(e)}")

    def onBgColorClick(self):
        """Open color picker initialized with the current background color"""
        try:
            view = Krita.instance().activeWindow().activeView()  # type: ignore
            if not view:
                return

            bg_color = view.backgroundColor()
            components = bg_color.components()
            # Get current color to initialize dialog (R,G,B from Krita: BGR order)
            initial_color = QColor(
                int(components[2] * 255),
                int(components[1] * 255),
                int(components[0] * 255),
            )

            color = QColorDialog.getColor(initial=initial_color)
            if color.isValid():
                managed = ManagedColor("RGBA", "U8", "")
                comps = managed.components()
                comps[2] = color.redF()
                comps[1] = color.greenF()
                comps[0] = color.blueF()
                comps[3] = 1.0
                managed.setComponents(comps)
                view.setBackGroundColor(managed)
                self.updateColorInfo()

                hex_code = "#{:02X}{:02X}{:02X}".format(color.red(), color.green(), color.blue())
                self.addColorToHistory(hex_code)
                self.bg_color_label.setTextAndColor(hex_code, hex_code)
                self.bg_color_button.setStyleSheet(f"background-color: {hex_code};")

        except Exception as e:
            self.showError(f"BG Picker Error: {str(e)}")
            
    def setBackGroundColor(self, color_hex):
        """Set the clicked color as the new background color using ManagedColor"""
        try:
            view = Krita.instance().activeWindow().activeView() # type: ignore
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
                view.setBackGroundColor(color)
                self.updateColorInfo()
                self.addColorToHistory(color_hex)

        except Exception as e:
            self.showError(f"FG Set Error: {str(e)}")
            
    def setForeGroundColor(self, color_hex):
        """Set the clicked color as the new foreground color using ManagedColor"""
        try:
            view = Krita.instance().activeWindow().activeView() # type: ignore
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
