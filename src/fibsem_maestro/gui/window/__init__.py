from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FIB-SEM Maestro")
        self.resize(1280, 800)

        # toolbar
        menu_bar = self.menuBar()
        menu_bar.addMenu("File")
        menu_bar.addMenu("Workflow")
        menu_bar.addMenu("Help")

        # central widget
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # vertical splitter
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        root_layout.addWidget(v_splitter)

        # horizontal splitter
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        v_splitter.addWidget(h_splitter)

        # scrollable panel with actions
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(120)
        left_placeholder = QWidget()  # replace with real content
        left_scroll.setWidget(left_placeholder)
        h_splitter.addWidget(left_scroll)

        # form panel
        self.form_container = QWidget()
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        h_splitter.addWidget(self.form_container)

        # splitter proportions
        h_splitter.setStretchFactor(0, 1)
        h_splitter.setStretchFactor(1, 4)

        # bottom panel
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        bottom_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        bottom_layout.addWidget(self.progress_bar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)  # cap memory usage
        self.log_view.setFixedHeight(120)
        bottom_layout.addWidget(self.log_view)

        v_splitter.addWidget(bottom)

        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

    def set_form(self, form_scroll: QScrollArea) -> None:
        """Drop a FormBuilder scroll area into the central panel."""
        layout = self.form_container.layout()
        # clear any previous form
        while layout.count():
            layout.takeAt(0).widget().deleteLater()
        layout.addWidget(form_scroll)

    def append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def set_progress(self, value: int) -> None:
        """Set progress bar value (0–100)."""
        self.progress_bar.setValue(value)
