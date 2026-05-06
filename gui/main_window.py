from __future__ import annotations

import os
import sys
import threading

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from providers.fivesim import FiveSimError, FiveSimProvider
from providers.sms_base import BotSettings, SmsConfig


class Worker(QObject):
    finished = pyqtSignal()
    log_line = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, settings: BotSettings):
        super().__init__()
        self.settings = settings
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def should_stop(self) -> bool:
        return self._stop.is_set()

    @pyqtSlot()
    def run(self) -> None:
        try:
            # Import here so the window opens without loading Selenium / selenium-wire.
            from app import run_bot

            def log(msg: str) -> None:
                self.log_line.emit(str(msg))

            run_bot(self.settings, log=log, should_stop=self.should_stop)
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Auto Gmail Creator — 5sim")
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        form = QFormLayout()
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("5sim API key (Bearer token)")
        self.country = QLineEdit("netherlands")
        self.operator = QLineEdit("any")
        self.product = QLineEdit("google")
        self.base_url = QLineEdit("https://5sim.net/v1")

        self.user_csv = QLineEdit(os.path.join(os.getcwd(), "User.csv"))
        btn_csv = QPushButton("Browse…")
        btn_csv.clicked.connect(self._browse_csv)
        csv_row = QHBoxLayout()
        csv_row.addWidget(self.user_csv)
        csv_row.addWidget(btn_csv)

        self.auto_gen = QCheckBox("Auto-generate user info from data/*.csv")
        self.auto_gen.setChecked(True)
        self.auto_count = QSpinBox()
        self.auto_count.setRange(1, 9999)
        self.auto_count.setValue(10)

        self.socks = QLineEdit()
        self.socks.setPlaceholderText("Optional socks5://user:pass@host:port")
        self.headless = QCheckBox("Headless Chrome")

        self.wait_s = QSpinBox()
        self.wait_s.setRange(1, 30)
        self.wait_s.setValue(4)
        self.retries = QSpinBox()
        self.retries.setRange(1, 50)
        self.retries.setValue(10)

        self.data_dir = QLineEdit(os.path.join(os.getcwd(), "data"))

        env_tok = os.environ.get("FIVESIM_TOKEN", "").strip()
        if env_tok:
            self.token.setText(env_tok)

        form.addRow("5sim API token", self.token)
        form.addRow("Country", self.country)
        form.addRow("Operator", self.operator)
        form.addRow("Product", self.product)
        form.addRow("API base URL", self.base_url)
        form.addRow("User CSV", csv_row)
        form.addRow(self.auto_gen)
        form.addRow("Auto-generate count", self.auto_count)
        form.addRow("SOCKS proxy (optional)", self.socks)
        form.addRow(self.headless)
        form.addRow("Wait (s)", self.wait_s)
        form.addRow("Max retries", self.retries)
        form.addRow("Data directory", self.data_dir)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_profile = QPushButton("Test profile (balance)")
        self.btn_products = QPushButton("Guest products")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._request_stop)
        self.btn_profile.clicked.connect(self._test_profile)
        self.btn_products.clicked.connect(self._guest_products)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_profile)
        btn_row.addWidget(self.btn_products)
        layout.addLayout(btn_row)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

    def _browse_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "User.csv", "", "CSV (*.csv)")
        if path:
            self.user_csv.setText(path)

    def _append_log(self, line: str) -> None:
        self.log_view.append(line)

    def _settings(self) -> BotSettings:
        sms = SmsConfig(
            api_token=self.token.text().strip(),
            country=self.country.text().strip() or "netherlands",
            operator=self.operator.text().strip() or "any",
            product=self.product.text().strip() or "google",
            base_url=self.base_url.text().strip() or "https://5sim.net/v1",
        )
        socks = self.socks.text().strip() or None
        return BotSettings(
            sms=sms,
            auto_generate_userinfo=self.auto_gen.isChecked(),
            auto_generate_number=int(self.auto_count.value()),
            user_csv_path=self.user_csv.text().strip(),
            wait=int(self.wait_s.value()),
            request_max_try=int(self.retries.value()),
            socks_proxy=socks,
            headless=self.headless.isChecked(),
            include_refer_url=False,
            data_dir=self.data_dir.text().strip() or "./data",
        )

    def _on_worker_finished(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._thread = None
        self._worker = None

    def _start(self) -> None:
        settings = self._settings()
        if not settings.sms.api_token:
            QMessageBox.warning(self, "Token", "Enter your 5sim API token.")
            return
        if self._thread is not None and self._thread.isRunning():
            return

        self._worker = Worker(settings)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.log_line.connect(self._append_log)
        self._worker.failed.connect(
            lambda m: self._append_log(f"ERROR: {m}"),
        )
        self._thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _request_stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        self._append_log("Stop requested…")
        self.btn_stop.setEnabled(False)

    def _test_profile(self) -> None:
        settings = self._settings()
        if not settings.sms.api_token:
            QMessageBox.warning(self, "Token", "Enter your 5sim API token.")
            return
        try:
            p = FiveSimProvider(settings.sms).profile()
            self._append_log(repr(p))
        except FiveSimError as e:
            self._append_log(f"Profile error: {e}")

    def _guest_products(self) -> None:
        c = self.country.text().strip() or "netherlands"
        o = self.operator.text().strip() or "any"
        try:
            prov = FiveSimProvider(SmsConfig(api_token=self.token.text().strip()))
            out = prov.guest_products(c, o)
            self._append_log(repr(out)[:8000])
        except FiveSimError as e:
            self._append_log(f"Guest products error: {e}")


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(780, 680)
    w.show()
    sys.exit(app.exec())
