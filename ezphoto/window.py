from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSettings, QSignalBlocker, QSize, QTimer, Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStyle,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ezphoto.canvas import ImageCanvas
from ezphoto.i18n import LANGUAGES, automatic_language, translate
from ezphoto.imaging import adjust_image, apply_filter, crop_image, open_image, resize_image


class Histogram(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(110)
        self.setMaximumHeight(140)
        self.set_image(None)

    def set_image(self, image: Image.Image | None) -> None:
        self._channels = image.convert("RGB").histogram()[:768] if image else None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#191b1e"))
        if not self._channels:
            return
        chart = self.rect().adjusted(8, 10, -8, -8)
        colors = (QColor(235, 99, 84, 170), QColor(102, 183, 135, 155), QColor(95, 149, 223, 170))
        for index, color in enumerate(colors):
            values = self._channels[index * 256 : (index + 1) * 256]
            peak = max(values, default=1) or 1
            path = QPainterPath()
            path.moveTo(chart.left(), chart.bottom())
            for step, value in enumerate(values):
                point_x = chart.left() + chart.width() * step / 255
                point_y = chart.bottom() - chart.height() * value / peak
                path.lineTo(point_x, point_y)
            path.lineTo(chart.right(), chart.bottom())
            painter.setPen(QPen(color, 1))
            painter.setBrush(color)
            painter.drawPath(path)


class ResizeDialog(QDialog):
    def __init__(self, width: int, height: int, text, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("resize"))
        self._ratio = width / height
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.width_input = QSpinBox()
        self.height_input = QSpinBox()
        for field in (self.width_input, self.height_input):
            field.setRange(1, 30_000)
        self.width_input.setValue(width)
        self.height_input.setValue(height)
        self.keep_ratio = QCheckBox(text("keep_ratio"))
        self.keep_ratio.setChecked(True)
        self.width_input.valueChanged.connect(self._width_changed)
        self.height_input.valueChanged.connect(self._height_changed)
        form.addRow(text("width"), self.width_input)
        form.addRow(text("height"), self.height_input)
        layout.addLayout(form)
        layout.addWidget(self.keep_ratio)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _width_changed(self, width: int) -> None:
        if self.keep_ratio.isChecked():
            self.height_input.blockSignals(True)
            self.height_input.setValue(round(width / self._ratio))
            self.height_input.blockSignals(False)

    def _height_changed(self, height: int) -> None:
        if self.keep_ratio.isChecked():
            self.width_input.blockSignals(True)
            self.width_input.setValue(round(height * self._ratio))
            self.width_input.blockSignals(False)


class EditorWindow(QMainWindow):
    _SLIDERS = ("brightness", "contrast", "saturation", "exposure", "warmth", "sharpness")

    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings()
        self._language_preference = self.settings.value("language", "auto")
        self.language = automatic_language() if self._language_preference == "auto" else self._language_preference
        self.image: Image.Image | None = None
        self.image_path: Path | None = None
        self.dirty = False
        self.undo_history: list[Image.Image] = []
        self.redo_history: list[Image.Image] = []
        self.adjustment_sliders: dict[str, QSlider] = {}
        self.slider_value_labels: dict[str, QLabel] = {}
        self._language_actions: dict[str, QAction] = {}
        self._preview_image: Image.Image | None = None
        self._crop_button: QPushButton | None = None
        self._apply_button: QPushButton | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(55)
        self._preview_timer.timeout.connect(self._render_preview)
        self._build_window()
        self._build_toolbar()
        self._build_menus()
        self._update_state()
        self.resize(1280, 820)
        self.setMinimumSize(800, 590)

    def t(self, key: str) -> str:
        return translate(key, self.language)

    def _build_window(self) -> None:
        self.setWindowTitle("ezPhoto")
        self._apply_palette()
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 15, 20, 0)
        root.setSpacing(9)

        heading = QHBoxLayout()
        brand = QLabel("ezPhoto")
        brand_font = QFont(self.font())
        brand_font.setPointSize(20)
        brand_font.setWeight(QFont.Weight.Bold)
        brand.setFont(brand_font)
        self._set_text_color(brand, "#f0a185")
        self._tagline = QLabel()
        tagline_font = QFont(self.font())
        tagline_font.setPointSize(8)
        tagline_font.setWeight(QFont.Weight.DemiBold)
        self._tagline.setFont(tagline_font)
        self._set_text_color(self._tagline, "#a0a09d")
        heading.addWidget(brand)
        heading.addSpacing(11)
        heading.addWidget(self._tagline)
        heading.addStretch()
        self._language_picker = QComboBox()
        self._language_picker.setFixedWidth(132)
        self._language_picker.addItem(self.t("auto"), "auto")
        for code, name in LANGUAGES.items():
            self._language_picker.addItem(name, code)
        self._language_picker.setCurrentIndex(max(0, self._language_picker.findData(self._language_preference)))
        self._language_picker.currentIndexChanged.connect(self._change_language)
        heading.addWidget(self._language_picker)
        root.addLayout(heading)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        root.addWidget(self.toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(238)
        self.tabs.setMaximumWidth(330)
        self.tabs.addTab(self._build_adjustments_tab(), "")
        self.tabs.addTab(self._build_effects_tab(), "")
        self.tabs.addTab(self._build_details_tab(), "")
        self.canvas = ImageCanvas(self.t)
        self.canvas.zoom_changed.connect(self._update_zoom)
        self.canvas.crop_changed.connect(self._update_crop_state)
        self.canvas.image_dropped.connect(self._open_dropped_file)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes((280, 920))
        root.addWidget(splitter, 1)

        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label, 1)
        self._zoom_label = QLabel()
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(12, 600)
        self._zoom_slider.setFixedWidth(105)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._slider_zoom)
        self.statusBar().addPermanentWidget(self._zoom_label)
        self.statusBar().addPermanentWidget(self._zoom_slider)
        self.statusBar().setSizeGripEnabled(False)
        self.setCentralWidget(central)
        self._update_translated_labels()

    def _apply_palette(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#202225"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ebe9e4"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#191b1e"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#282a2e"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ebe9e4"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#303237"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f0eeea"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#c96e50"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#747579"))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#747579"))
        self.setPalette(palette)
        QApplication.instance().setPalette(palette)
        application_fonts = {"Noto Sans", "Inter", "Ubuntu", "DejaVu Sans"}
        from PySide6.QtGui import QFontDatabase

        installed = set(QFontDatabase.families())
        self.setFont(QFont(next((name for name in ("Noto Sans", "Inter", "Ubuntu", "DejaVu Sans") if name in installed), QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()), 10))

    @staticmethod
    def _set_text_color(widget: QWidget, color: str) -> None:
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
        widget.setPalette(palette)

    def _build_toolbar(self) -> None:
        style = self.style()
        self._open_action = self._action("open", "Ctrl+O", style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), self.open_file)
        self._save_action = self._action("save", "Ctrl+S", style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), self.save_file)
        self._undo_action = self._action("undo", "Ctrl+Z", style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack), self.undo)
        self._redo_action = self._action("redo", "Ctrl+Shift+Z", style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), self.redo)
        for action in (self._open_action, self._save_action):
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        for action in (self._undo_action, self._redo_action):
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        self._crop_action = self._action("crop", "C", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton), self.toggle_crop)
        self._crop_action.setCheckable(True)
        self.toolbar.addAction(self._crop_action)
        self._export_action = self._action("export", "Ctrl+Shift+E", style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), self.export_file)
        self.toolbar.addAction(self._export_action)

    def _action(self, key: str, shortcut: str, icon, callback) -> QAction:
        action = QAction(icon, self.t(key), self)
        action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        self.addAction(action)
        return action

    def _build_menus(self) -> None:
        self._menus = {key: self.menuBar().addMenu("") for key in ("file", "edit", "image_menu", "language_menu")}
        for action in (self._open_action, self._save_action, self._export_action):
            self._menus["file"].addAction(action)
        self._menus["file"].addSeparator()
        self._quit_action = QAction("", self)
        self._quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self._quit_action.triggered.connect(self.close)
        self._menus["file"].addAction(self._quit_action)
        for action in (self._undo_action, self._redo_action):
            self._menus["edit"].addAction(action)
        self._menus["edit"].addSeparator()
        self._menus["edit"].addAction(self._action("reset", "Ctrl+0", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton), self.reset_adjustments))
        for label, slot in (("rotate_left", lambda: self._transform(self.image.rotate(90, expand=True) if self.image else None)), ("rotate_right", lambda: self._transform(self.image.rotate(-90, expand=True) if self.image else None)), ("flip_horizontal", self.flip_horizontal), ("flip_vertical", self.flip_vertical), ("resize", self.resize_image)):
            action = self._action(label, "", self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight), slot)
            self._menus["image_menu"].addAction(action)
        for code, language in (("auto", self.t("auto")), *(LANGUAGES.items())):
            action = QAction(language, self)
            action.setCheckable(True)
            action.setChecked(("auto" if self.settings.value("language", "auto") == "auto" else self.language) == code)
            action.triggered.connect(lambda checked=False, chosen=code: self._select_language(chosen))
            self._menus["language_menu"].addAction(action)
            self._language_actions[code] = action

    def _build_adjustments_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 15, 14, 14)
        layout.setSpacing(13)
        self._adjust_heading = QLabel()
        self._set_text_color(self._adjust_heading, "#eee9e2")
        layout.addWidget(self._adjust_heading)
        for name in self._SLIDERS:
            row = QVBoxLayout()
            header = QHBoxLayout()
            title = QLabel()
            value = QLabel("0")
            value.setMinimumWidth(33)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(-100, 100)
            slider.setValue(0)
            slider.valueChanged.connect(lambda amount, key=name, label=value: self._slider_changed(key, amount, label))
            title.setObjectName(f"slider_{name}")
            row.addLayout(header)
            header.addWidget(title)
            header.addStretch()
            header.addWidget(value)
            row.addWidget(slider)
            layout.addLayout(row)
            self.adjustment_sliders[name] = slider
            self.slider_value_labels[name] = value
        layout.addSpacing(5)
        self._apply_button = QPushButton()
        self._apply_button.setDefault(True)
        self._apply_button.clicked.connect(self.apply_adjustments)
        self._reset_button = QPushButton()
        self._reset_button.clicked.connect(self.reset_adjustments)
        layout.addWidget(self._apply_button)
        layout.addWidget(self._reset_button)
        layout.addStretch()
        self._crop_instructions = QLabel()
        self._crop_instructions.setWordWrap(True)
        self._set_text_color(self._crop_instructions, "#f0a185")
        layout.addWidget(self._crop_instructions)
        self._crop_button = QPushButton()
        self._crop_button.setEnabled(False)
        self._crop_button.clicked.connect(self.apply_crop)
        self._crop_button.setVisible(False)
        layout.addWidget(self._crop_button)
        return page

    def _build_effects_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 15, 14, 14)
        layout.setSpacing(9)
        self._effects_heading = QLabel()
        self._set_text_color(self._effects_heading, "#eee9e2")
        layout.addWidget(self._effects_heading)
        for key, filter_name in (("grayscale", "grayscale"), ("sepia", "sepia"), ("negative", "negative"), ("blur", "blur"), ("sharpen", "sharpen")):
            button = QPushButton()
            button.setObjectName(f"filter_{filter_name}")
            button.clicked.connect(lambda checked=False, selected=filter_name: self._apply_filter(selected))
            setattr(self, f"_filter_{filter_name}", button)
            layout.addWidget(button)
        layout.addSpacing(12)
        self._transform_heading = QLabel()
        self._set_text_color(self._transform_heading, "#eee9e2")
        layout.addWidget(self._transform_heading)
        for key, callback in (
            ("rotate_left", lambda: self._transform(self.image.rotate(90, expand=True) if self.image else None)),
            ("rotate_right", lambda: self._transform(self.image.rotate(-90, expand=True) if self.image else None)),
            ("flip_horizontal", self.flip_horizontal),
            ("flip_vertical", self.flip_vertical),
            ("resize", self.resize_image),
        ):
            button = QPushButton()
            button.clicked.connect(callback)
            setattr(self, f"_effect_{key}", button)
            layout.addWidget(button)
        layout.addStretch()
        return page

    def _build_details_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 15, 14, 14)
        layout.setSpacing(10)
        self._file_heading = QLabel()
        self._set_text_color(self._file_heading, "#eee9e2")
        layout.addWidget(self._file_heading)
        self._file_value = QLabel()
        self._file_value.setWordWrap(True)
        layout.addWidget(self._file_value)
        self._dimensions_value = QLabel()
        layout.addWidget(self._dimensions_value)
        self._mode_value = QLabel()
        self._mode_value.setWordWrap(True)
        layout.addWidget(self._mode_value)
        self._histogram_heading = QLabel()
        self._set_text_color(self._histogram_heading, "#eee9e2")
        layout.addWidget(self._histogram_heading)
        self._histogram = Histogram()
        layout.addWidget(self._histogram)
        layout.addStretch()
        return page

    def _update_translated_labels(self) -> None:
        if not hasattr(self, "_tagline"):
            return
        self._tagline.setText(self.t("app_tagline"))
        self._tabs_labels = (self.t("adjust"), self.t("filters"), self.t("details"))
        for index, label in enumerate(self._tabs_labels):
            self.tabs.setTabText(index, label)
        self._adjust_heading.setText(self.t("adjust_photo"))
        for key, slider in self.adjustment_sliders.items():
            self.findChild(QLabel, f"slider_{key}").setText(self.t(key))
            slider.setToolTip(self.t(key))
        self._crop_instructions.setText(self.t("select_crop"))
        self._apply_button.setText(self.t("apply"))
        self._reset_button.setText(self.t("reset"))
        self._crop_instructions.setText(self.t("select_crop"))
        self._crop_button.setText(self.t("apply_crop"))
        self._effects_heading.setText(self.t("effects"))
        for key in ("grayscale", "sepia", "negative", "blur", "sharpen"):
            getattr(self, f"_filter_{key}").setText(self.t(key))
        self._transform_heading.setText(self.t("transform"))
        for key in ("rotate_left", "rotate_right", "flip_horizontal", "flip_vertical", "resize"):
            getattr(self, f"_effect_{key}").setText(self.t(key))
        self._file_heading.setText(self.t("file_info"))
        self._histogram_heading.setText(self.t("history"))
        self._menus[self._menu_key].setTitle(self.t(self._menu_key)) if hasattr(self, "_menu_key") else None
        if hasattr(self, "_menus"):
            for key, menu in self._menus.items():
                menu.setTitle(self.t(key))
            self._quit_action.setText(self.t("quit"))
        if self._language_actions:
            self._language_actions["auto"].setText(self.t("auto"))
            for code, name in LANGUAGES.items():
                self._language_actions[code].setText(name)
        for action, key in ((self._open_action, "open"), (self._save_action, "save"), (self._undo_action, "undo"), (self._redo_action, "redo"), (self._crop_action, "crop"), (self._export_action, "export")):
            action.setText(self.t(key))
        self._update_state()

    def _change_language(self, index: int) -> None:
        code = self._language_picker.itemData(index)
        if code:
            self._select_language(code)

    def _select_language(self, code: str) -> None:
        self._language_preference = code
        self.settings.setValue("language", code)
        self.language = automatic_language() if code == "auto" else code
        if hasattr(self, "_language_picker"):
            with QSignalBlocker(self._language_picker):
                self._language_picker.setCurrentIndex(max(0, self._language_picker.findData(code)))
        self._update_translated_labels()
        self._update_state()

    def _slider_changed(self, key: str, amount: int, label: QLabel) -> None:
        label.setText(f"{amount:+d}" if amount else "0")
        self._preview_timer.start()

    def _current_adjustments(self) -> dict[str, int]:
        return {key: slider.value() for key, slider in self.adjustment_sliders.items()}

    def _render_preview(self) -> None:
        if self.image is None:
            return
        maximum = 1600
        if max(self.image.size) > maximum:
            scale = maximum / max(self.image.size)
            preview = self.image.resize((round(self.image.width * scale), round(self.image.height * scale)), Image.Resampling.BILINEAR)
        else:
            preview = self.image
        self._preview_image = adjust_image(preview, **self._current_adjustments())
        self.canvas.set_image(self._preview_image)

    def apply_adjustments(self) -> None:
        if self.image is None or not any(self._current_adjustments().values()):
            return
        self._preview_timer.stop()
        updated = adjust_image(self.image, **self._current_adjustments())
        self._commit(updated)
        self._reset_sliders()

    def reset_adjustments(self) -> None:
        self._preview_timer.stop()
        self._reset_sliders()
        self._preview_image = None
        self._show_image()

    def _reset_sliders(self) -> None:
        for key, slider in self.adjustment_sliders.items():
            with QSignalBlocker(slider):
                slider.setValue(0)
            self.slider_value_labels[key].setText("0")

    def _apply_filter(self, name: str) -> None:
        if self.image is not None:
            self._commit(apply_filter(self.image, name))

    def _transform(self, image: Image.Image | None) -> None:
        if image is not None:
            self._commit(image)

    def flip_horizontal(self) -> None:
        if self.image is not None:
            self._commit(self.image.transpose(Image.Transpose.FLIP_LEFT_RIGHT))

    def flip_vertical(self) -> None:
        if self.image is not None:
            self._commit(self.image.transpose(Image.Transpose.FLIP_TOP_BOTTOM))

    def resize_image(self) -> None:
        if self.image is None:
            return
        dialog = ResizeDialog(self.image.width, self.image.height, self.t, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._commit(resize_image(self.image, dialog.width_input.value(), dialog.height_input.value()))

    def toggle_crop(self, enabled: bool | None = None) -> None:
        enabled = self._crop_action.isChecked() if enabled is None else enabled
        self._crop_action.setChecked(enabled)
        self.canvas.set_crop_mode(enabled)
        self._crop_button.setVisible(enabled)
        self._crop_instructions.setVisible(enabled)
        self._apply_button.setVisible(not enabled)
        self._reset_button.setVisible(not enabled)
        self.tabs.setCurrentIndex(0)

    def _update_crop_state(self, selection) -> None:
        box = self.canvas.crop_box
        self._crop_button.setEnabled(bool(box))
        if box and self.image:
            width, height = box[2] - box[0], box[3] - box[1]
            self._crop_button.setText(f"{self.t('apply_crop')}  ·  {width} × {height}")
        else:
            self._crop_button.setText(self.t("apply_crop"))

    def apply_crop(self) -> None:
        if self.image is not None and self.canvas.crop_box:
            self._commit(crop_image(self.image, self.canvas.crop_box))
            self.toggle_crop(False)

    def _commit(self, updated: Image.Image) -> None:
        if self.image is None:
            return
        self.undo_history.append(self.image.copy())
        if len(self.undo_history) > 40:
            self.undo_history.pop(0)
        self.redo_history.clear()
        self.image = updated
        self.dirty = True
        self._preview_image = None
        self.canvas.reset_crop()
        self._show_image()

    def undo(self) -> None:
        if self.image is not None and self.undo_history:
            self.redo_history.append(self.image.copy())
            self.image = self.undo_history.pop()
            self.dirty = True
            self.reset_adjustments()
            self._update_state()

    def redo(self) -> None:
        if self.image is not None and self.redo_history:
            self.undo_history.append(self.image.copy())
            self.image = self.redo_history.pop()
            self.dirty = True
            self.reset_adjustments()
            self._update_state()

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("open"), "", f"{self.t('open_images')} (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp *.gif)")
        if path:
            self._load_file(path)

    def _open_dropped_file(self, path: str) -> None:
        self._load_file(path)

    def _load_file(self, path: str) -> None:
        try:
            loaded = open_image(path)
        except Exception as error:
            QMessageBox.critical(self, self.t("error_title"), str(error))
            return
        if self.image is not None and self.dirty and not self._confirm_discard():
            return
        self.image = loaded
        self.image_path = Path(path)
        self.undo_history.clear()
        self.redo_history.clear()
        self.dirty = False
        self._preview_image = None
        self.reset_adjustments()
        self._update_state()

    def _confirm_discard(self) -> bool:
        message = QMessageBox(self)
        message.setWindowTitle(self.t("confirm_title"))
        message.setText(self.t("confirm_open"))
        message.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        message.setDefaultButton(QMessageBox.StandardButton.Save)
        response = message.exec()
        if response == QMessageBox.StandardButton.Save:
            return self.save_file()
        return response == QMessageBox.StandardButton.Discard

    def save_file(self) -> bool:
        if self.image is None:
            return False
        if self.image_path is None:
            return self.export_file()
        try:
            self._save_image(self.image_path)
        except Exception as error:
            QMessageBox.critical(self, self.t("export_title"), str(error))
            return False
        self.dirty = False
        self._update_state()
        return True

    def export_file(self) -> bool:
        if self.image is None:
            return False
        path, _ = QFileDialog.getSaveFileName(self, self.t("export_title"), str(self.image_path or "ezPhoto.png"), f"{self.t('save_images')} (*.png *.jpg *.jpeg *.webp *.tif *.tiff)")
        if not path:
            return False
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".png")
        try:
            self._save_image(target)
        except Exception as error:
            QMessageBox.critical(self, self.t("export_title"), str(error))
            return False
        self.image_path = target
        self.dirty = False
        self._update_state()
        return True

    def _save_image(self, path: Path) -> None:
        image = self.image.copy()
        options = {}
        if path.suffix.lower() in (".jpg", ".jpeg"):
            image = image.convert("RGB")
            options["quality"] = 95
            options["optimize"] = True
        image.save(path, **options)

    def _show_image(self) -> None:
        if self.image is not None:
            self.canvas.set_image(self.image)
            self._histogram.set_image(self.image)
            self._file_value.setText(self.image_path.name if self.image_path else self.t("untitled"))
            self._dimensions_value.setText(f"{self.t('dimensions')}  ·  {self.image.width:,} × {self.image.height:,}")
            self._mode_value.setText(f"{self.t('color_mode')}  ·  RGBA")
            self.status_label.setText(f"{self.image.width:,} × {self.image.height:,} px")
        else:
            self.canvas.set_image(None)
            self._histogram.set_image(None)
            self._file_value.setText(self.t("no_image"))
            self._dimensions_value.setText("")
            self._mode_value.setText("")
            self.status_label.setText(self.t("no_image"))

    def _update_zoom(self, zoom: float) -> None:
        if hasattr(self, "_zoom_slider"):
            self._zoom_label.setText(f"{self.t('zoom')}  {zoom:.0%}")
            with QSignalBlocker(self._zoom_slider):
                self._zoom_slider.setValue(round(zoom * 100))

    def _slider_zoom(self, amount: int) -> None:
        if self.canvas._zoom > 0:
            self.canvas.zoom_by(amount / 100 / self.canvas._zoom)

    def _update_state(self) -> None:
        if not hasattr(self, "_save_action"):
            return
        loaded = self.image is not None
        self._save_action.setEnabled(loaded and self.dirty)
        self._export_action.setEnabled(loaded)
        self._undo_action.setEnabled(loaded and bool(self.undo_history))
        self._redo_action.setEnabled(loaded and bool(self.redo_history))
        self._crop_action.setEnabled(loaded)
        for action in self._menus.get("image_menu", ()).actions() if hasattr(self, "_menus") else ():
            action.setEnabled(loaded)
        if hasattr(self, "_zoom_slider"):
            self._zoom_slider.setEnabled(loaded)
        name = self.image_path.name if self.image_path else self.t("untitled")
        self.setWindowTitle(f"{'● ' if self.dirty else ''}{name} — ezPhoto" if loaded else "ezPhoto")
        if hasattr(self, "_file_value") and self.image is not None:
            self._file_value.setText(name)

    def closeEvent(self, event) -> None:
        if self.image is not None and self.dirty and not self._confirm_discard():
            event.ignore()
            return
        event.accept()