from collections.abc import Callable

from PIL import Image
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget


def image_to_pixmap(image: Image.Image) -> QPixmap:
    image = image.convert("RGBA")
    qt_image = QImage(
        image.tobytes("raw", "RGBA"),
        image.width,
        image.height,
        image.width * 4,
        QImage.Format.Format_RGBA8888,
    ).copy()
    return QPixmap.fromImage(qt_image)


class ImageCanvas(QWidget):
    zoom_changed = Signal(float)
    crop_changed = Signal(QRect)
    image_dropped = Signal(str)

    def __init__(self, text: Callable[[str], str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._pixmap = QPixmap()
        self._image_size = (0, 0)
        self._zoom = 1.0
        self._pan = QPointF()
        self._pan_origin = QPointF()
        self._drag_start = None
        self._drag_end = None
        self._crop_mode = False
        self._on_screen = QRectF()
        self.setMinimumSize(300, 250)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    @property
    def crop_box(self) -> tuple[int, int, int, int] | None:
        if not self._drag_start or not self._drag_end or self._on_screen.isEmpty():
            return None
        selection = QRectF(self._drag_start, self._drag_end).normalized().intersected(self._on_screen)
        scale = self._on_screen.width() / self._image_size[0]
        left = round((selection.left() - self._on_screen.left()) / scale)
        top = round((selection.top() - self._on_screen.top()) / scale)
        right = round((selection.right() - self._on_screen.left()) / scale)
        bottom = round((selection.bottom() - self._on_screen.top()) / scale)
        return (left, top, right, bottom) if right > left and bottom > top else None

    def set_image(self, image: Image.Image | None) -> None:
        self._pixmap = image_to_pixmap(image) if image else QPixmap()
        self._image_size = image.size if image else (0, 0)
        self._drag_start = self._drag_end = None
        self._pan = QPointF()
        self._zoom = 1.0
        self.update()
        self.zoom_changed.emit(self._zoom)

    def set_crop_mode(self, enabled: bool) -> None:
        self._crop_mode = enabled
        self._drag_start = self._drag_end = None
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.crop_changed.emit(QRect())
        self.update()

    def reset_crop(self) -> None:
        self._drag_start = self._drag_end = None
        self.crop_changed.emit(QRect())
        self.update()

    def zoom_by(self, factor: float) -> None:
        if self._pixmap.isNull():
            return
        self._zoom = min(6.0, max(0.12, self._zoom * factor))
        self.zoom_changed.emit(self._zoom)
        self.update()

    def _fit_scale(self) -> float:
        if not self._image_size[0] or not self.width() or not self.height():
            return 1.0
        return min(
            (self.width() - 64) / self._image_size[0],
            (self.height() - 64) / self._image_size[1],
            1.0,
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#17191c"))
        if self._pixmap.isNull():
            painter.setPen(QColor("#eeeeeb"))
            title_font = painter.font()
            title_font.setPointSize(18)
            title_font.setWeight(600)
            painter.setFont(title_font)
            painter.drawText(self.rect().adjusted(36, -18, -36, -18), Qt.AlignmentFlag.AlignCenter, self._text("drop_image"))
            hint_font = painter.font()
            hint_font.setPointSize(10)
            hint_font.setWeight(400)
            painter.setFont(hint_font)
            painter.setPen(QColor("#929498"))
            painter.drawText(self.rect().adjusted(36, 24, -36, -24), Qt.AlignmentFlag.AlignCenter, self._text("or_open"))
            return

        scale = self._fit_scale() * self._zoom
        width, height = self._image_size[0] * scale, self._image_size[1] * scale
        self._on_screen = QRectF(
            (self.width() - width) / 2 + self._pan.x(),
            (self.height() - height) / 2 + self._pan.y(),
            width,
            height,
        )
        tile = 16
        for y in range(max(0, int(self._on_screen.top())), min(self.height(), int(self._on_screen.bottom())), tile):
            for x in range(max(0, int(self._on_screen.left())), min(self.width(), int(self._on_screen.right())), tile):
                shade = "#deded8" if (x // tile + y // tile) % 2 == 0 else "#b9bab5"
                painter.fillRect(QRect(x, y, tile, tile).intersected(self.rect()), QColor(shade))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self._on_screen, self._pixmap, QRectF(self._pixmap.rect()))

        if self._crop_mode and self._drag_start and self._drag_end:
            selection = QRectF(self._drag_start, self._drag_end).normalized()
            shade = QColor(15, 16, 18, 145)
            painter.fillRect(QRectF(self._on_screen.left(), self._on_screen.top(), self._on_screen.width(), max(0, selection.top() - self._on_screen.top())), shade)
            painter.fillRect(QRectF(self._on_screen.left(), selection.bottom(), self._on_screen.width(), max(0, self._on_screen.bottom() - selection.bottom())), shade)
            painter.fillRect(QRectF(self._on_screen.left(), selection.top(), max(0, selection.left() - self._on_screen.left()), selection.height()), shade)
            painter.fillRect(QRectF(selection.right(), selection.top(), max(0, self._on_screen.right() - selection.right()), selection.height()), shade)
            painter.setPen(QPen(QColor("#ffffff"), 1.5, Qt.PenStyle.DashLine))
            painter.drawRect(selection)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._on_screen.contains(event.position()):
            return
        if self._crop_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = self._drag_end = event.position()
        elif event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._drag_start = event.position()
            self._pan_origin = self._pan
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._crop_mode and self._drag_start is not None:
            self._drag_end = event.position()
            self.crop_changed.emit(QRect(self._drag_start.toPoint(), self._drag_end.toPoint()).normalized())
            self.update()
        elif self._drag_start is not None and event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.MiddleButton):
            self._pan = self._pan_origin + event.position() - self._drag_start
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._crop_mode and self._drag_start is not None:
            self._drag_end = event.position()
            self.crop_changed.emit(QRect(self._drag_start.toPoint(), self._drag_end.toPoint()).normalized())
            self.update()
        elif self._drag_start is not None:
            self._drag_start = None
            self.unsetCursor()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.zoom_by(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.image_dropped.emit(urls[0].toLocalFile())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()