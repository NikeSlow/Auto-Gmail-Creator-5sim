from __future__ import annotations

import os
import sys
import threading
import csv
import json
import time

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from providers.fivesim import FiveSimError, FiveSimProvider
from providers.sms_base import BotSettings, SmsConfig

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# #region agent log
_WORKSPACE_DEBUG_LOG = r"c:\dev\telegram-mcp\debug-edd7d7.log"
_PROJECT_DEBUG_LOG = _WORKSPACE_DEBUG_LOG
# #endregion
DEBUG_SESSION_ID = "edd7d7"


def _debug_enabled() -> bool:
    # #region agent log
    return True
    # #endregion


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # #region agent log
    if not _debug_enabled():
        return
    payload = {
        "sessionId": DEBUG_SESSION_ID,
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=True) + "\n"
    paths = [_PROJECT_DEBUG_LOG]
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        paths.append(os.path.join(temp, "debug-edd7d7-edd7d7.log"))
    errors: list[str] = []
    ok_any = False
    for p in paths:
        try:
            parent = os.path.dirname(p)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
            ok_any = True
        except Exception as e:
            errors.append(f"{p}: {e!r}")
    if not ok_any:
        fail_path = os.path.join(_PROJECT_ROOT, "debug-edd7d7-write-fail.txt")
        try:
            with open(fail_path, "a", encoding="utf-8") as ff:
                ff.write(line)
                for err in errors:
                    ff.write(err + "\n")
        except Exception:
            pass
    # #endregion


class ProxyScraperWorker(QObject):
    """Runs scripts.proxy_scraper.ProxyManager off the GUI thread."""

    finished = pyqtSignal()
    log_line = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, data_dir: str, max_workers: int, max_per_type: int):
        super().__init__()
        self.data_dir = data_dir
        self.max_workers = max_workers
        self.max_per_type = max_per_type
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def should_stop(self) -> bool:
        return self._stop.is_set()

    @pyqtSlot()
    def run(self) -> None:
        try:
            from scripts.proxy_scraper import ProxyManager

            def log(msg: str) -> None:
                self.log_line.emit(str(msg))

            ProxyManager.run(
                data_dir=self.data_dir,
                log=log,
                max_workers=self.max_workers,
                max_per_type=self.max_per_type,
                should_stop=self.should_stop,
            )
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self.finished.emit()


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
        _debug_log(
            "H6",
            "gui.main_window.Worker.run",
            "Worker thread entered run_bot",
            {"data_dir": self.settings.data_dir},
        )
        try:
            # Import here so the window opens without loading Selenium / selenium-wire.
            from app import run_bot

            def log(msg: str) -> None:
                self.log_line.emit(str(msg))

            run_bot(self.settings, log=log, should_stop=self.should_stop)
            _debug_log(
                "H6",
                "gui.main_window.Worker.run",
                "run_bot returned normally",
                {},
            )
        except Exception as e:
            _debug_log(
                "H6",
                "gui.main_window.Worker.run",
                "run_bot raised",
                {"error": str(e)},
            )
            self.failed.emit(str(e))
        finally:
            self.finished.emit()


class NameListEditorDialog(QDialog):
    def __init__(self, first_names: list[str], last_names: list[str], parent=None):
        super().__init__(parent)
        _debug_log(
            "H2",
            "gui/main_window.py:NameListEditorDialog.__init__",
            "Name editor dialog opened",
            {"first_count": len(first_names), "last_count": len(last_names)},
        )
        self.setWindowTitle("Edit Name CSVs")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Edit values below. Empty rows are ignored on save."))

        tables_row = QHBoxLayout()
        self.first_table = self._make_table(first_names)
        self.last_table = self._make_table(last_names)
        tables_row.addWidget(self.first_table)
        tables_row.addWidget(self.last_table)
        layout.addLayout(tables_row)

        actions = QHBoxLayout()
        self.btn_add_first = QPushButton("Add row (first)")
        self.btn_add_last = QPushButton("Add row (last)")
        self.btn_delete_first = QPushButton("Delete selected (first)")
        self.btn_delete_last = QPushButton("Delete selected (last)")
        self.btn_add_first.clicked.connect(lambda: self.first_table.insertRow(self.first_table.rowCount()))
        self.btn_add_last.clicked.connect(lambda: self.last_table.insertRow(self.last_table.rowCount()))
        self.btn_delete_first.clicked.connect(lambda: self._delete_selected_rows(self.first_table))
        self.btn_delete_last.clicked.connect(lambda: self._delete_selected_rows(self.last_table))
        actions.addWidget(self.btn_add_first)
        actions.addWidget(self.btn_add_last)
        actions.addWidget(self.btn_delete_first)
        actions.addWidget(self.btn_delete_last)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_table(self, values: list[str]) -> QTableWidget:
        table = QTableWidget(max(len(values), 12), 1)
        header = table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setHorizontalHeaderLabels(["Name"])
        for idx, value in enumerate(values):
            table.setItem(idx, 0, QTableWidgetItem(value))
        return table

    @staticmethod
    def _collect_values(table: QTableWidget) -> list[str]:
        out: list[str] = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            val = (item.text().strip() if item else "").strip()
            if val:
                out.append(val)
        # preserve order, remove duplicates
        return list(dict.fromkeys(out))

    @staticmethod
    def _delete_selected_rows(table: QTableWidget) -> None:
        selected = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for row in selected:
            table.removeRow(row)
        if table.rowCount() == 0:
            table.insertRow(0)

    def get_values(self) -> tuple[list[str], list[str]]:
        return self._collect_values(self.first_table), self._collect_values(self.last_table)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Auto Gmail Creator — 5sim")
        # #region agent log
        _debug_log(
            "H1",
            "gui/main_window.py:MainWindow.__init__",
            "GUI boot snapshot",
            {
                "python": sys.version.split()[0],
                "platform": sys.platform,
                "cwd": os.getcwd(),
                "default_data_dir": os.path.join(os.getcwd(), "data"),
                "fivesim_env_set": bool(os.environ.get("FIVESIM_TOKEN", "").strip()),
                "auto_gmail_debug_env": os.environ.get("AUTO_GMAIL_DEBUG", ""),
            },
        )
        # #endregion
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._scraper_thread: QThread | None = None
        self._scraper_worker: ProxyScraperWorker | None = None
        self._build_ui()
        self._refresh_readiness_status()

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

        self.auto_gen = QCheckBox("Auto-generate user info from data/*.csv")
        self.auto_gen.setChecked(True)
        self.auto_gen.setEnabled(False)
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

        self.proxy_workers = QSpinBox()
        self.proxy_workers.setRange(1, 200)
        self.proxy_workers.setValue(50)
        self.proxy_max_per_type = QSpinBox()
        self.proxy_max_per_type.setRange(10, 2000)
        self.proxy_max_per_type.setValue(400)

        env_tok = os.environ.get("FIVESIM_TOKEN", "").strip()
        if env_tok:
            self.token.setText(env_tok)

        form.addRow("5sim API token", self.token)
        form.addRow("Country", self.country)
        form.addRow("Operator", self.operator)
        form.addRow("Product", self.product)
        form.addRow("API base URL", self.base_url)
        form.addRow("User data mode", self.auto_gen)
        form.addRow("Auto-generate count", self.auto_count)
        form.addRow("SOCKS proxy (optional)", self.socks)
        form.addRow(self.headless)
        form.addRow("Wait (s)", self.wait_s)
        form.addRow("Max retries", self.retries)
        data_dir_row = QHBoxLayout()
        data_dir_row.addWidget(self.data_dir)
        btn_browse_data = QPushButton("Browse…")
        btn_browse_data.clicked.connect(self._browse_data_dir)
        btn_open_data = QPushButton("Open folder")
        btn_open_data.clicked.connect(self._open_data_dir)
        data_dir_row.addWidget(btn_browse_data)
        data_dir_row.addWidget(btn_open_data)
        data_dir_wrap = QWidget()
        data_dir_wrap.setLayout(data_dir_row)
        form.addRow("Data directory", data_dir_wrap)
        form.addRow("Proxy scraper workers", self.proxy_workers)
        form.addRow("Proxy max per list type", self.proxy_max_per_type)

        layout.addLayout(form)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_init_data = QPushButton("Initialize required CSVs")
        self.btn_edit_name_csvs = QPushButton("Edit name CSVs")
        self.btn_profile = QPushButton("Test profile (balance)")
        self.btn_products = QPushButton("Guest products")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._request_stop)
        self.btn_init_data.clicked.connect(self._initialize_required_csvs)
        self.btn_edit_name_csvs.clicked.connect(self._edit_name_csvs)
        self.btn_profile.clicked.connect(self._test_profile)
        self.btn_products.clicked.connect(self._guest_products)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_init_data)
        btn_row.addWidget(self.btn_edit_name_csvs)
        btn_row.addWidget(self.btn_profile)
        btn_row.addWidget(self.btn_products)
        layout.addLayout(btn_row)

        scraper_row = QHBoxLayout()
        self.btn_fetch_proxies = QPushButton("Fetch & validate proxies → data/Proxy_DB.csv")
        self.btn_stop_scraper = QPushButton("Stop scraper")
        self.btn_stop_scraper.setEnabled(False)
        self.btn_fetch_proxies.clicked.connect(self._start_scraper)
        self.btn_stop_scraper.clicked.connect(self._request_stop_scraper)
        scraper_row.addWidget(self.btn_fetch_proxies)
        scraper_row.addWidget(self.btn_stop_scraper)
        scraper_row.addStretch()
        layout.addLayout(scraper_row)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.token.textChanged.connect(self._refresh_readiness_status)
        self.data_dir.textChanged.connect(self._refresh_readiness_status)

    def _refresh_readiness_status(self) -> None:
        data_dir = self.data_dir.text().strip() or "./data"
        first_name_path = os.path.join(data_dir, "First_Name_DB.csv")
        last_name_path = os.path.join(data_dir, "Last_Name_DB.csv")
        proxy_path = os.path.join(data_dir, "Proxy_DB.csv")

        token_ok = bool(self.token.text().strip())
        first_count = len(self._read_single_col_csv(first_name_path))
        last_count = len(self._read_single_col_csv(last_name_path))
        proxy_ok = os.path.exists(proxy_path)

        checks = [
            f"Token: {'OK' if token_ok else 'Missing'}",
            f"First names CSV: {'OK' if first_count > 0 else 'Missing/empty'} ({first_count})",
            f"Last names CSV: {'OK' if last_count > 0 else 'Missing/empty'} ({last_count})",
            f"Proxy CSV: {'OK' if proxy_ok else 'Not found'}",
        ]
        _debug_log(
            "H1",
            "gui/main_window.py:_refresh_readiness_status",
            "Readiness status computed",
            {
                "data_dir": data_dir,
                "token_ok": token_ok,
                "first_count": first_count,
                "last_count": last_count,
                "proxy_ok": proxy_ok,
            },
        )
        self.status_label.setText("Readiness: " + " | ".join(checks))

    def _append_log(self, line: str) -> None:
        self.log_view.append(line)

    def _browse_data_dir(self) -> None:
        start = self.data_dir.text().strip() or os.getcwd()
        path = QFileDialog.getExistingDirectory(self, "Select data folder", start)
        if path:
            self.data_dir.setText(path)

    def _open_data_dir(self) -> None:
        path = os.path.abspath(self.data_dir.text().strip() or "./data")
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, "Folder", str(e))
            return
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')  # nosec B607
        else:
            os.system(f'xdg-open "{path}"')  # nosec B607

    @staticmethod
    def _read_single_col_csv(path: str) -> list[str]:
        if not os.path.exists(path):
            _debug_log(
                "H1",
                "gui/main_window.py:_read_single_col_csv",
                "CSV does not exist",
                {"path": path},
            )
            return []
        rows: list[str] = []
        with open(path, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                value = row[0].strip()
                if value:
                    rows.append(value)
        return list(dict.fromkeys(rows))

    @staticmethod
    def _write_single_col_csv(path: str, values: list[str]) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for value in values:
                writer.writerow([value])

    def _ensure_name_dbs(self, data_dir: str) -> tuple[str, str]:
        os.makedirs(data_dir, exist_ok=True)
        first_name_path = os.path.join(data_dir, "First_Name_DB.csv")
        last_name_path = os.path.join(data_dir, "Last_Name_DB.csv")

        default_first_names = [
            "Alex", "Sam", "Jordan", "Taylor", "Chris", "Jamie", "Morgan", "Riley"
        ]
        default_last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson"
        ]

        if not os.path.exists(first_name_path):
            with open(first_name_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for name in default_first_names:
                    writer.writerow([name])
        if not os.path.exists(last_name_path):
            with open(last_name_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for name in default_last_names:
                    writer.writerow([name])
        _debug_log(
            "H3",
            "gui/main_window.py:_ensure_name_dbs",
            "Ensured name CSV files",
            {
                "data_dir": data_dir,
                "first_exists": os.path.exists(first_name_path),
                "last_exists": os.path.exists(last_name_path),
            },
        )
        return first_name_path, last_name_path

    def _edit_name_csvs(self) -> None:
        data_dir = self.data_dir.text().strip() or "./data"
        _debug_log(
            "H2",
            "gui/main_window.py:_edit_name_csvs",
            "Edit CSV requested",
            {"data_dir": data_dir},
        )
        try:
            first_name_path, last_name_path = self._ensure_name_dbs(data_dir)
            first_names = self._read_single_col_csv(first_name_path)
            last_names = self._read_single_col_csv(last_name_path)

            dlg = NameListEditorDialog(first_names, last_names, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            updated_first, updated_last = dlg.get_values()
            if not updated_first or not updated_last:
                _debug_log(
                    "H2",
                    "gui/main_window.py:_edit_name_csvs",
                    "Save rejected due to empty list",
                    {
                        "first_count": len(updated_first),
                        "last_count": len(updated_last),
                    },
                )
                QMessageBox.warning(
                    self,
                    "Invalid data",
                    "Both first and last name lists must contain at least one value.",
                )
                return
            self._write_single_col_csv(first_name_path, updated_first)
            self._write_single_col_csv(last_name_path, updated_last)
            _debug_log(
                "H2",
                "gui/main_window.py:_edit_name_csvs",
                "CSV save completed",
                {
                    "first_saved": len(updated_first),
                    "last_saved": len(updated_last),
                },
            )
            self._append_log(
                f"Saved name CSVs ({len(updated_first)} first / {len(updated_last)} last)."
            )
            self._refresh_readiness_status()
        except Exception as e:
            _debug_log(
                "H2",
                "gui/main_window.py:_edit_name_csvs",
                "Exception thrown",
                {"error": str(e)},
            )
            QMessageBox.critical(self, "Name CSV editor failed", str(e))

    def _initialize_required_csvs(self) -> None:
        data_dir = self.data_dir.text().strip() or "./data"
        try:
            first_name_path, last_name_path = self._ensure_name_dbs(data_dir)
            self._append_log(f"Ready: {first_name_path}")
            self._append_log(f"Ready: {last_name_path}")
            QMessageBox.information(
                self,
                "CSV files ready",
                "Created missing First_Name_DB.csv and Last_Name_DB.csv in Data directory.",
            )
            self._refresh_readiness_status()
        except Exception as e:
            QMessageBox.critical(self, "CSV setup failed", str(e))

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
            auto_generate_userinfo=True,
            auto_generate_number=int(self.auto_count.value()),
            user_csv_path="",
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
        self._refresh_scraper_controls_busy_state()

    def _refresh_scraper_controls_busy_state(self) -> None:
        bot_busy = self._thread is not None and self._thread.isRunning()
        scraper_busy = (
            self._scraper_thread is not None and self._scraper_thread.isRunning()
        )
        self.btn_fetch_proxies.setEnabled(not bot_busy and not scraper_busy)
        self.proxy_workers.setEnabled(not scraper_busy)
        self.proxy_max_per_type.setEnabled(not scraper_busy)
        if scraper_busy:
            self.btn_start.setEnabled(False)
        elif not bot_busy:
            self.btn_start.setEnabled(True)

    def _on_scraper_finished(self) -> None:
        self.btn_stop_scraper.setEnabled(False)
        self._scraper_thread = None
        self._scraper_worker = None
        self._refresh_scraper_controls_busy_state()

    def _start_scraper(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.warning(
                self,
                "Busy",
                "Stop the Gmail bot before running the proxy scraper.",
            )
            return
        if self._scraper_thread is not None and self._scraper_thread.isRunning():
            return

        data_dir = self.data_dir.text().strip() or "./data"
        self._scraper_worker = ProxyScraperWorker(
            data_dir=data_dir,
            max_workers=int(self.proxy_workers.value()),
            max_per_type=int(self.proxy_max_per_type.value()),
        )
        self._scraper_thread = QThread()
        self._scraper_worker.moveToThread(self._scraper_thread)
        self._scraper_thread.started.connect(self._scraper_worker.run)
        self._scraper_worker.finished.connect(self._scraper_thread.quit)
        self._scraper_worker.finished.connect(self._scraper_worker.deleteLater)
        self._scraper_thread.finished.connect(self._scraper_thread.deleteLater)
        self._scraper_worker.finished.connect(self._on_scraper_finished)
        self._scraper_worker.log_line.connect(self._append_log)
        self._scraper_worker.failed.connect(
            lambda m: self._append_log(f"PROXY SCRAPER ERROR: {m}"),
        )
        self._scraper_thread.start()
        self.btn_stop_scraper.setEnabled(True)
        self._refresh_scraper_controls_busy_state()
        self._refresh_readiness_status()

    def _request_stop_scraper(self) -> None:
        if self._scraper_worker is not None:
            self._scraper_worker.stop()
        self._append_log("Proxy scraper stop requested…")

    def _start(self) -> None:
        if self._scraper_thread is not None and self._scraper_thread.isRunning():
            QMessageBox.warning(
                self,
                "Busy",
                "Wait for the proxy scraper to finish or stop it first.",
            )
            return
        settings = self._settings()
        # #region agent log
        proxy_csv = os.path.join(settings.data_dir, "Proxy_DB.csv")
        first_csv = os.path.join(settings.data_dir, "First_Name_DB.csv")
        last_csv = os.path.join(settings.data_dir, "Last_Name_DB.csv")
        _debug_log(
            "H2",
            "gui/main_window.py:_start",
            "Pre-flight readiness at Start click",
            {
                "token_present": bool(settings.sms.api_token),
                "data_dir": settings.data_dir,
                "data_dir_exists": os.path.isdir(settings.data_dir),
                "proxy_csv_exists": os.path.exists(proxy_csv),
                "first_csv_exists": os.path.exists(first_csv),
                "last_csv_exists": os.path.exists(last_csv),
                "first_count": len(self._read_single_col_csv(first_csv)),
                "last_count": len(self._read_single_col_csv(last_csv)),
                "headless": settings.headless,
                "auto_count": settings.auto_generate_number,
                "socks_present": bool(settings.socks_proxy),
            },
        )
        # #endregion
        _debug_log(
            "H4",
            "gui/main_window.py:_start",
            "Start requested",
            {
                "token_present": bool(settings.sms.api_token),
                "data_dir": settings.data_dir,
                "auto_count": settings.auto_generate_number,
            },
        )
        if not settings.sms.api_token:
            QMessageBox.warning(self, "Token", "Enter your 5sim API token.")
            return
        try:
            self._ensure_name_dbs(settings.data_dir)
        except Exception as e:
            QMessageBox.critical(self, "CSV setup failed", str(e))
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
        self._refresh_scraper_controls_busy_state()

    def _request_stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        self._append_log("Stop requested…")
        self.btn_stop.setEnabled(False)

    def _test_profile(self) -> None:
        settings = self._settings()
        # #region agent log
        _debug_log(
            "H4",
            "gui/main_window.py:_test_profile",
            "Test profile clicked",
            {"token_present": bool(settings.sms.api_token)},
        )
        # #endregion
        if not settings.sms.api_token:
            QMessageBox.warning(self, "Token", "Enter your 5sim API token.")
            return
        try:
            p = FiveSimProvider(settings.sms).profile()
            # #region agent log
            _debug_log(
                "H4",
                "gui/main_window.py:_test_profile",
                "Profile fetched",
                {
                    "type": type(p).__name__,
                    "keys": sorted(list(p.keys())) if isinstance(p, dict) else None,
                },
            )
            # #endregion
            self._append_log(repr(p))
        except FiveSimError as e:
            # #region agent log
            _debug_log(
                "H4",
                "gui/main_window.py:_test_profile",
                "Profile error",
                {"error_type": type(e).__name__, "error_msg": str(e)},
            )
            # #endregion
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
    _debug_log(
        "H5",
        "gui/main_window.py:main",
        "GUI main entered",
        {"cwd": os.getcwd()},
    )
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(780, 680)
    w.show()
    sys.exit(app.exec())
