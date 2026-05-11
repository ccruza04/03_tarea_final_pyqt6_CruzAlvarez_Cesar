import csv
import sys
from datetime import datetime
from pathlib import Path

import psutil
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDateEdit,   # ← IMPORTANTE
)


class MonitorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Monitor del sistema")
        self.resize(1100, 650)

        self.output_file = Path("../monitor.txt")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_data)

        self._build_ui()
        self._apply_styles()
        self._ensure_header()
        self.load_file_to_table()

    # ----------------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        title = QLabel("Monitor de sistema")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Toma de métricas en tiempo real y consulta histórica")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_menu = QHBoxLayout()
        self.btn_toma = QPushButton("📊 Toma de datos")
        self.btn_visor = QPushButton("📁 Visor")
        self.btn_toma.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_visor.clicked.connect(self.switch_to_viewer)
        top_menu.addStretch()
        top_menu.addWidget(self.btn_toma)
        top_menu.addWidget(self.btn_visor)
        top_menu.addStretch()

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_capture_page())
        self.stack.addWidget(self._build_viewer_page())

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addLayout(top_menu)
        main_layout.addWidget(self.stack)

    def _build_capture_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        form = QFormLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(3600)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" s")
        form.addRow("Intervalo de chequeo:", self.interval_spin)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.btn_start = QPushButton("▶ Iniciar toma")
        self.btn_stop = QPushButton("⏹ Finalizar")
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.start_capture)
        self.btn_stop.clicked.connect(self.stop_capture)
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_stop)
        actions.addStretch()
        layout.addLayout(actions)

        self.status_label = QLabel("Estado: detenido")
        self.status_label.setObjectName("status")
        self.last_data_label = QLabel("Sin datos todavía.")
        layout.addWidget(self.status_label)
        layout.addWidget(self.last_data_label)
        layout.addStretch()
        return page

    def _build_viewer_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)

        # ------------------------------------------------------------------
        # BUSCADOR CON SELECTOR DE FECHA + HORA
        # ------------------------------------------------------------------
        search_layout = QHBoxLayout()

        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDisplayFormat("yyyy-MM-dd")
        self.date_selector.setDate(datetime.now().date())

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Hora opcional (ej: 14:32)")

        self.btn_search = QPushButton("🔎 Buscar")
        self.btn_reset = QPushButton("↺ Mostrar todo")

        self.btn_search.clicked.connect(self.search_metrics)
        self.btn_reset.clicked.connect(self.load_file_to_table)
        self.search_input.returnPressed.connect(self.search_metrics)

        search_layout.addWidget(QLabel("Fecha:"))
        search_layout.addWidget(self.date_selector)
        search_layout.addWidget(QLabel("Hora:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_search)
        search_layout.addWidget(self.btn_reset)

        # ------------------------------------------------------------------
        # TABLA
        # ------------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)

        controls = QHBoxLayout()
        self.btn_refresh = QPushButton("Actualizar listado")
        self.btn_clear = QPushButton("Vaciar archivo")
        self.btn_refresh.clicked.connect(self.load_file_to_table)
        self.btn_clear.clicked.connect(self.clear_file)
        self.result_label = QLabel("")
        controls.addWidget(self.btn_refresh)
        controls.addWidget(self.btn_clear)
        controls.addStretch()
        controls.addWidget(self.result_label)

        layout.addLayout(search_layout)
        layout.addWidget(self.table)
        layout.addLayout(controls)
        return page

    # ----------------------------------------------------------------------
    # ESTILOS
    # ----------------------------------------------------------------------

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QWidget { font-size: 14px; background-color: #F3F4F6; color: #111827; }
            #title { font-size: 28px; font-weight: 700; color: #1F2937; }
            #subtitle { color: #4B5563; margin-bottom: 8px; }
            #card {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 12px;
                padding: 14px;
            }
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 500;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton:disabled { background: #9CA3AF; color: #E5E7EB; }
            QLineEdit, QSpinBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px;
            }
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #F9FAFB;
                gridline-color: #D1D5DB;
                selection-background-color: #2563EB;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #E5E7EB;
                padding: 6px;
                border: 1px solid #D1D5DB;
                font-weight: 600;
            }
            #status { font-weight: 600; color: #065F46; }
        """)

    # ----------------------------------------------------------------------
    # LÓGICA
    # ----------------------------------------------------------------------

    def _ensure_header(self) -> None:
        if not self.output_file.exists() or self.output_file.stat().st_size == 0:
            with self.output_file.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"])

    def start_capture(self) -> None:
        self.timer.start(self.interval_spin.value() * 1000)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("Estado: capturando")
        self.capture_data()

    def stop_capture(self) -> None:
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Estado: detenido")

    def capture_data(self) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cpu = round(psutil.cpu_percent(interval=None), 2)
        ram = round(psutil.virtual_memory().percent, 2)
        disk = round(psutil.disk_usage("/").percent, 2)
        net = psutil.net_io_counters()
        row = [stamp, cpu, ram, disk, int(net.bytes_sent), int(net.bytes_recv)]

        with self.output_file.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

        self.last_data_label.setText(f"Última toma: {stamp} | CPU: {cpu}% | RAM: {ram}% | Disco: {disk}%")
        if self.stack.currentIndex() == 1:
            self.load_file_to_table()

    def load_file_to_table(self) -> None:
        rows = self._read_rows()
        self._render_rows(rows)
        self.result_label.setText(f"Registros: {len(rows)}")

    def search_metrics(self) -> None:
        selected_date = self.date_selector.date().toString("yyyy-MM-dd")
        hour_query = self.search_input.text().strip()

        rows = self._read_rows()

        filtered = [row for row in rows if row[0].startswith(selected_date)]

        if hour_query:
            hour_query = hour_query.lower()
            filtered = [row for row in filtered if hour_query in row[0].lower()]

        self._render_rows(filtered)
        self.result_label.setText(f"Coincidencias: {len(filtered)}")

    def _read_rows(self) -> list[list[str]]:
        self._ensure_header()
        with self.output_file.open("r", newline="", encoding="utf-8") as f:
            all_rows = list(csv.reader(f))
        return all_rows[1:] if len(all_rows) > 1 else []

    def _render_rows(self, rows: list[list[str]]) -> None:
        headers = ["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(value))

    def clear_file(self) -> None:
        answer = QMessageBox.question(self, "Confirmar", "¿Seguro que quieres vaciar el archivo?")
        if answer == QMessageBox.StandardButton.Yes:
            with self.output_file.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"])
            self.load_file_to_table()

    def switch_to_viewer(self) -> None:
        self.load_file_to_table()
        self.stack.setCurrentIndex(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MonitorWindow()
    window.show()
    sys.exit(app.exec())
