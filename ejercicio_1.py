import csv
import sys
from datetime import datetime
from pathlib import Path

import psutil
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
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
)


class MonitorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Monitor del sistema")
        self.resize(980, 520)

        self.output_file = Path("monitor.txt")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_data)

        self._build_ui()
        self._ensure_header()
        self.load_file_to_table()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        top_menu = QHBoxLayout()
        self.btn_toma = QPushButton("Toma de datos")
        self.btn_visor = QPushButton("Visor")
        self.btn_toma.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_visor.clicked.connect(lambda: self.switch_to_viewer())
        top_menu.addWidget(self.btn_toma)
        top_menu.addWidget(self.btn_visor)
        top_menu.addStretch()
        main_layout.addLayout(top_menu)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_capture_page())
        self.stack.addWidget(self._build_viewer_page())
        main_layout.addWidget(self.stack)

    def _build_capture_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(3600)
        self.interval_spin.setValue(5)
        form.addRow("Intervalo (segundos):", self.interval_spin)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.btn_start = QPushButton("Iniciar toma")
        self.btn_stop = QPushButton("Finalizar")
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.start_capture)
        self.btn_stop.clicked.connect(self.stop_capture)
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_stop)
        actions.addStretch()
        layout.addLayout(actions)

        self.last_data_label = QLabel("Sin datos todavía.")
        layout.addWidget(self.last_data_label)

        return page

    def _build_viewer_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        self.btn_refresh = QPushButton("Actualizar listado")
        self.btn_clear = QPushButton("Vaciar archivo")
        self.btn_refresh.clicked.connect(self.load_file_to_table)
        self.btn_clear.clicked.connect(self.clear_file)
        controls.addWidget(self.btn_refresh)
        controls.addWidget(self.btn_clear)
        controls.addStretch()
        layout.addLayout(controls)

        return page

    def _ensure_header(self) -> None:
        if not self.output_file.exists() or self.output_file.stat().st_size == 0:
            with self.output_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"])

    def start_capture(self) -> None:
        interval_ms = self.interval_spin.value() * 1000
        self.timer.start(interval_ms)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.capture_data()

    def stop_capture(self) -> None:
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def capture_data(self) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cpu = round(psutil.cpu_percent(interval=None), 2)
        ram = round(psutil.virtual_memory().percent, 2)
        disk = round(psutil.disk_usage("/").percent, 2)
        net = psutil.net_io_counters()
        net_sent = int(net.bytes_sent)
        net_recv = int(net.bytes_recv)

        row = [stamp, cpu, ram, disk, net_sent, net_recv]

        with self.output_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        self.last_data_label.setText(
            f"Última toma: {stamp} | CPU: {cpu}% | RAM: {ram}% | Disco: {disk}%"
        )

        if self.stack.currentIndex() == 1:
            self.load_file_to_table()

    def load_file_to_table(self) -> None:
        self._ensure_header()

        with self.output_file.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        if not rows:
            self.table.setRowCount(0)
            return

        data_rows = rows[1:]
        self.table.setRowCount(len(data_rows))
        self.table.setColumnCount(len(rows[0]))
        self.table.setHorizontalHeaderLabels(rows[0])

        for i, row in enumerate(data_rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(value))

    def clear_file(self) -> None:
        answer = QMessageBox.question(
            self,
            "Confirmar",
            "¿Seguro que quieres vaciar el archivo de monitorización?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            with self.output_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["hora", "cpu", "ram", "disco", "net_enviada", "net_recibida"])
            self.load_file_to_table()

    def switch_to_viewer(self) -> None:
        self.load_file_to_table()
        self.stack.setCurrentIndex(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MonitorWindow()
    window.show()
    sys.exit(app.exec())
