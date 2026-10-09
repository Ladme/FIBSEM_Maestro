from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPolygonF
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

_YELLOW = QColor("#f5c400")
_BLACK = QColor("#1a1a1a")


class DangerBanner(QWidget):
    """
    A hazard-striped strip with a "DANGER MODE" label, shown while danger mode is on.

    Yellow and black diagonal stripes read as a hazard at a glance and stay
    distinct from the red used for errors. The banner starts hidden; the owner
    shows and hides it.

    Args:
        parent: The parent widget, if any.
    """

    _HEIGHT = 28  # px
    _STRIPE = 14  # px, width of one stripe along the banner

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self._HEIGHT)

        label = QLabel("DANGER MODE")
        font = label.font()
        font.setBold(True)
        font.setPointSize(11)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        label.setFont(font)
        label.setStyleSheet(
            f"background: {_BLACK.name()}; color: {_YELLOW.name()}; "
            "padding: 1px 14px; border-radius: 3px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()

        self.hide()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        """Paint black diagonal stripes on a yellow ground across the whole banner."""
        _ = a0
        height = self.height()
        stripe = self._STRIPE

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), _YELLOW)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_BLACK)
            # each stripe is a parallelogram leaning right by the banner height
            for x in range(-height, self.width() + height, 2 * stripe):
                painter.drawPolygon(
                    QPolygonF(
                        [
                            QPointF(x, height),
                            QPointF(x + stripe, height),
                            QPointF(x + stripe + height, 0),
                            QPointF(x + height, 0),
                        ]
                    )
                )
        finally:
            painter.end()
