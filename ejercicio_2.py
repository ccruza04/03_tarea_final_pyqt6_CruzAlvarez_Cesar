import sqlite3
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

DB_PATH = Path("libros.db")


class BibliotecaDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._crear_tabla()

    def _crear_tabla(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS libros (
                    isbn TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    autor TEXT NOT NULL,
                    descripcion TEXT
                )
                """
            )

    def nuevo_libro(self, isbn: str, titulo: str, autor: str, descripcion: str):
        with self.conn:
            self.conn.execute(
                "INSERT INTO libros(isbn, titulo, autor, descripcion) VALUES(?, ?, ?, ?)",
                (isbn, titulo, autor, descripcion),
            )

    def consultar(self, isbn: str):
        cursor = self.conn.execute("SELECT * FROM libros WHERE isbn = ?", (isbn,))
        return cursor.fetchone()

    def editar(self, isbn: str, titulo: str, autor: str, descripcion: str):
        with self.conn:
            cur = self.conn.execute(
                "UPDATE libros SET titulo = ?, autor = ?, descripcion = ? WHERE isbn = ?",
                (titulo, autor, descripcion, isbn),
            )
        return cur.rowcount > 0

    def borrar(self, isbn: str):
        with self.conn:
            cur = self.conn.execute("DELETE FROM libros WHERE isbn = ?", (isbn,))
        return cur.rowcount > 0

    def listado(self):
        cursor = self.conn.execute(
            "SELECT isbn, titulo, autor, descripcion FROM libros ORDER BY titulo COLLATE NOCASE"
        )
        return cursor.fetchall()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = BibliotecaDB(DB_PATH)
        self.setWindowTitle("Gestión de Libros - PyQt6 + SQLite")
        self.resize(950, 600)
        self._init_ui()
        self._recargar_tabla()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        form_box = QGroupBox("Datos del libro")
        form_layout = QFormLayout(form_box)

        self.isbn_input = QLineEdit()
        self.titulo_input = QLineEdit()
        self.autor_input = QLineEdit()
        self.descripcion_input = QPlainTextEdit()
        self.descripcion_input.setPlaceholderText("Descripción del libro...")
        self.descripcion_input.setFixedHeight(100)

        form_layout.addRow("ISBN:", self.isbn_input)
        form_layout.addRow("Título:", self.titulo_input)
        form_layout.addRow("Autor:", self.autor_input)
        form_layout.addRow("Descripción:", self.descripcion_input)

        btn_grid = QGridLayout()
        self.btn_nuevo = QPushButton("Nuevo libro")
        self.btn_consulta = QPushButton("Consulta por ISBN")
        self.btn_editar = QPushButton("Edición")
        self.btn_borrar = QPushButton("Borrado por ISBN")
        self.btn_listado = QPushButton("Listado")
        self.btn_limpiar = QPushButton("Limpiar formulario")
        self.btn_salir = QPushButton("Salir")

        btn_grid.addWidget(self.btn_nuevo, 0, 0)
        btn_grid.addWidget(self.btn_consulta, 0, 1)
        btn_grid.addWidget(self.btn_editar, 0, 2)
        btn_grid.addWidget(self.btn_borrar, 1, 0)
        btn_grid.addWidget(self.btn_listado, 1, 1)
        btn_grid.addWidget(self.btn_limpiar, 1, 2)

        top_layout = QVBoxLayout()
        top_layout.addWidget(form_box)
        top_layout.addLayout(btn_grid)

        table_box = QGroupBox("Listado de libros")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ISBN", "Título", "Autor", "Descripción"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._cargar_seleccion_a_form)
        table_layout.addWidget(self.table)

        footer = QHBoxLayout()
        self.lbl_estado = QLabel("Listo")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        footer.addWidget(self.lbl_estado)
        footer.addStretch()
        footer.addWidget(self.btn_salir)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(table_box)
        main_layout.addLayout(footer)

        self.btn_nuevo.clicked.connect(self._accion_nuevo)
        self.btn_consulta.clicked.connect(self._accion_consulta)
        self.btn_editar.clicked.connect(self._accion_editar)
        self.btn_borrar.clicked.connect(self._accion_borrar)
        self.btn_listado.clicked.connect(self._recargar_tabla)
        self.btn_limpiar.clicked.connect(self._limpiar_form)
        self.btn_salir.clicked.connect(self.close)

    def _valores_form(self):
        return (
            self.isbn_input.text().strip(),
            self.titulo_input.text().strip(),
            self.autor_input.text().strip(),
            self.descripcion_input.toPlainText().strip(),
        )

    def _validar_para_guardar(self):
        isbn, titulo, autor, _ = self._valores_form()
        if not isbn or not titulo or not autor:
            QMessageBox.warning(self, "Campos obligatorios", "ISBN, título y autor son obligatorios.")
            return False
        return True

    def _accion_nuevo(self):
        if not self._validar_para_guardar():
            return
        isbn, titulo, autor, descripcion = self._valores_form()
        try:
            self.db.nuevo_libro(isbn, titulo, autor, descripcion)
            self.lbl_estado.setText(f"Libro {isbn} creado.")
            self._recargar_tabla()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "ISBN duplicado", "Ya existe un libro con ese ISBN.")

    def _accion_consulta(self):
        isbn = self.isbn_input.text().strip()
        if not isbn:
            QMessageBox.information(self, "Consulta", "Introduce un ISBN para consultar.")
            return

        row = self.db.consultar(isbn)
        if not row:
            QMessageBox.information(self, "Consulta", f"No existe un libro con ISBN {isbn}.")
            return

        self.titulo_input.setText(row["titulo"])
        self.autor_input.setText(row["autor"])
        self.descripcion_input.setPlainText(row["descripcion"] or "")
        self.lbl_estado.setText(f"Libro {isbn} cargado.")

    def _accion_editar(self):
        if not self._validar_para_guardar():
            return
        isbn, titulo, autor, descripcion = self._valores_form()
        ok = self.db.editar(isbn, titulo, autor, descripcion)
        if ok:
            self.lbl_estado.setText(f"Libro {isbn} actualizado.")
            self._recargar_tabla()
        else:
            QMessageBox.information(self, "Edición", f"No existe un libro con ISBN {isbn}.")

    def _accion_borrar(self):
        isbn = self.isbn_input.text().strip()
        if not isbn:
            QMessageBox.information(self, "Borrado", "Introduce un ISBN para borrar.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar borrado",
            f"¿Seguro que quieres borrar el libro con ISBN {isbn}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok = self.db.borrar(isbn)
        if ok:
            self.lbl_estado.setText(f"Libro {isbn} eliminado.")
            self._limpiar_form()
            self._recargar_tabla()
        else:
            QMessageBox.information(self, "Borrado", f"No existe un libro con ISBN {isbn}.")

    def _recargar_tabla(self):
        rows = self.db.listado()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["isbn"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["titulo"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["autor"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["descripcion"] or ""))
        self.table.resizeColumnsToContents()
        self.lbl_estado.setText(f"Listado actualizado ({len(rows)} libros).")

    def _limpiar_form(self):
        self.isbn_input.clear()
        self.titulo_input.clear()
        self.autor_input.clear()
        self.descripcion_input.clear()

    def _cargar_seleccion_a_form(self):
        items = self.table.selectedItems()
        if not items:
            return
        fila = items[0].row()
        self.isbn_input.setText(self.table.item(fila, 0).text())
        self.titulo_input.setText(self.table.item(fila, 1).text())
        self.autor_input.setText(self.table.item(fila, 2).text())
        self.descripcion_input.setPlainText(self.table.item(fila, 3).text())


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
