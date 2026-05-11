import sqlite3
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
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
    QTabWidget,
    QDialog,
    QCompleter,
)

DB_PATH = Path("libros.db")


# ---------------------------------------------------------
#   BASE DE DATOS
# ---------------------------------------------------------
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


# ---------------------------------------------------------
#   DIÁLOGO LISTADO
# ---------------------------------------------------------
class ListadoDialog(QDialog):
    def __init__(self, db: BibliotecaDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Listado de libros")
        self.resize(800, 500)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar por ISBN, título o autor...")
        search_layout.addWidget(QLabel("Filtro:"))
        search_layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ISBN", "Título", "Autor", "Descripción"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)

        footer = QHBoxLayout()
        self.lbl_info = QLabel("")
        footer.addWidget(self.lbl_info)
        footer.addStretch()
        footer.addWidget(btn_close)

        layout.addLayout(search_layout)
        layout.addWidget(self.table)
        layout.addLayout(footer)

        self.search_input.textChanged.connect(self._apply_filter)

    def _load_data(self):
        self._rows = list(self.db.listado())
        self._populate_table(self._rows)

    def _apply_filter(self):
        text = self.search_input.text().strip().lower()
        if not text:
            filtered = self._rows
        else:
            filtered = [
                r
                for r in self._rows
                if text in r["isbn"].lower()
                or text in r["titulo"].lower()
                or text in r["autor"].lower()
            ]
        self._populate_table(filtered)

    def _populate_table(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["isbn"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["titulo"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["autor"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["descripcion"] or ""))
        self.table.resizeColumnsToContents()
        self.lbl_info.setText(f"{len(rows)} libros mostrados")


# ---------------------------------------------------------
#   VENTANA PRINCIPAL
# ---------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = BibliotecaDB(DB_PATH)
        self.setWindowTitle("Gestión de Libros - PyQt6 + SQLite")
        self.resize(1000, 650)

        self._init_ui()
        self._apply_styles()
        self._configurar_autocompletado()

    def _init_ui(self):
        # Quitamos la barra de menú
        self.setMenuBar(None)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self._init_tab_nuevo()
        self._init_tab_buscar()
        self._init_tab_consultar()

        btn_listar_menu = QPushButton("Listar todo")
        btn_listar_menu.clicked.connect(self._accion_listar)


        menu_layout = QHBoxLayout()
        menu_layout.addWidget(btn_listar_menu)
        menu_layout.addStretch()

        main_layout.addLayout(menu_layout)
        main_layout.addWidget(self.tabs)

        self.lbl_estado = QLabel("Listo")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        footer = QHBoxLayout()
        footer.addWidget(self.lbl_estado)
        footer.addStretch()

        main_layout.addLayout(footer)

    # ---------------------------------------------------------
    #   AUTOCOMPLETADO ISBN – TÍTULO
    # ---------------------------------------------------------
    def _configurar_autocompletado(self):
        libros = self.db.listado()
        sugerencias = [f'{l["isbn"]} - {l["titulo"]}' for l in libros]

        completer = QCompleter(sugerencias)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.isbn_buscar.setCompleter(completer)

    # ---------------------------------------------------------
    #   PESTAÑA NUEVO LIBRO
    # ---------------------------------------------------------
    def _init_tab_nuevo(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_box = QGroupBox("Nuevo libro")
        form_layout = QFormLayout(form_box)

        self.isbn_nuevo = QLineEdit()
        self.titulo_nuevo = QLineEdit()
        self.autor_nuevo = QLineEdit()
        self.descripcion_nuevo = QPlainTextEdit()
        self.descripcion_nuevo.setFixedHeight(100)

        form_layout.addRow("ISBN:", self.isbn_nuevo)
        form_layout.addRow("Título:", self.titulo_nuevo)
        form_layout.addRow("Autor:", self.autor_nuevo)
        form_layout.addRow("Descripción:", self.descripcion_nuevo)

        btn_crear = QPushButton("Crear libro")
        btn_crear.clicked.connect(self._accion_crear)

        layout.addWidget(form_box)
        layout.addWidget(btn_crear)
        layout.addStretch()

        self.tabs.addTab(tab, "Nuevo libro")

    # ---------------------------------------------------------
    #   PESTAÑA BUSCAR / MODIFICAR / BORRAR
    # ---------------------------------------------------------
    def _init_tab_buscar(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_box = QGroupBox("Buscar / Modificar / Borrar libro")
        form_layout = QFormLayout(form_box)

        self.isbn_buscar = QLineEdit()
        self.titulo_buscar = QLineEdit()
        self.autor_buscar = QLineEdit()
        self.descripcion_buscar = QPlainTextEdit()
        self.descripcion_buscar.setFixedHeight(100)

        form_layout.addRow("ISBN:", self.isbn_buscar)
        form_layout.addRow("Título:", self.titulo_buscar)
        form_layout.addRow("Autor:", self.autor_buscar)
        form_layout.addRow("Descripción:", self.descripcion_buscar)

        btn_layout = QHBoxLayout()
        btn_buscar = QPushButton("Autorellenar")
        btn_modificar = QPushButton("Modificar libro")
        btn_borrar = QPushButton("Borrar libro")


        btn_buscar.clicked.connect(self._accion_buscar)
        btn_modificar.clicked.connect(self._accion_modificar)
        btn_borrar.clicked.connect(self._accion_borrar)


        btn_layout.addWidget(btn_buscar)
        btn_layout.addWidget(btn_modificar)
        btn_layout.addWidget(btn_borrar)

        btn_layout.addStretch()

        layout.addWidget(form_box)
        layout.addLayout(btn_layout)
        layout.addStretch()

        self.tabs.addTab(tab, "Buscar libro")


    # ---------------------------------------------------------
    #   PESTAÑA CONSULTAR
    # ---------------------------------------------------------
    def _init_tab_consultar(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_box = QGroupBox("Consultar por ISBN")
        form_layout = QFormLayout(form_box)

        self.isbn_consulta = QLineEdit()
        self.titulo_consulta = QLineEdit()
        self.autor_consulta = QLineEdit()
        self.descripcion_consulta = QPlainTextEdit()
        self.descripcion_consulta.setFixedHeight(100)

        self.titulo_consulta.setReadOnly(True)
        self.autor_consulta.setReadOnly(True)
        self.descripcion_consulta.setReadOnly(True)

        form_layout.addRow("ISBN:", self.isbn_consulta)
        form_layout.addRow("Título:", self.titulo_consulta)
        form_layout.addRow("Autor:", self.autor_consulta)
        form_layout.addRow("Descripción:", self.descripcion_consulta)

        btn_consultar = QPushButton("Consultar")
        btn_consultar.clicked.connect(self._accion_consultar)

        layout.addWidget(form_box)
        layout.addWidget(btn_consultar)
        layout.addStretch()

        self.tabs.addTab(tab, "Consultar por ISBN")

    # ---------------------------------------------------------
    #   ESTILOS
    # ---------------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QGroupBox::title {
            subcontrol-origin: padding;
            padding: 2px 8px;
            }

            QPushButton {
                background-color: #2563EB;
                color: white;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QLineEdit, QPlainTextEdit {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 4px;
            }
            """
        )

    # ---------------------------------------------------------
    #   VALIDACIÓN
    # ---------------------------------------------------------
    def _validar_campos(self, isbn: QLineEdit, titulo: QLineEdit, autor: QLineEdit):
        ok = True
        for w in (isbn, titulo, autor):
            w.setStyleSheet("")
        if not isbn.text().strip():
            isbn.setStyleSheet("border: 2px solid #DC2626;")
            ok = False
        if not titulo.text().strip():
            titulo.setStyleSheet("border: 2px solid #DC2626;")
            ok = False
        if not autor.text().strip():
            autor.setStyleSheet("border: 2px solid #DC2626;")
            ok = False
        if not ok:
            QMessageBox.warning(self, "Campos obligatorios", "ISBN, título y autor son obligatorios.")
        return ok

    # ---------------------------------------------------------
    #   ACCIONES
    # ---------------------------------------------------------
    def _accion_crear(self):
        isbn = self.isbn_nuevo.text().strip()
        titulo = self.titulo_nuevo.text().strip()
        autor = self.autor_nuevo.text().strip()
        descripcion = self.descripcion_nuevo.toPlainText().strip()

        if not self._validar_campos(self.isbn_nuevo, self.titulo_nuevo, self.autor_nuevo):
            return

        try:
            self.db.nuevo_libro(isbn, titulo, autor, descripcion)
            self.lbl_estado.setText(f"Libro {isbn} creado.")
            self._configurar_autocompletado()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "ISBN duplicado", "Ya existe un libro con ese ISBN.")

    def _accion_buscar(self):
        texto = self.isbn_buscar.text().strip()
        isbn = texto.split(" - ")[0] if " - " in texto else texto

        if not isbn:
            QMessageBox.information(self, "Buscar", "Introduce un ISBN para buscar.")
            return

        row = self.db.consultar(isbn)
        if not row:
            QMessageBox.information(self, "Buscar", f"No existe un libro con ISBN {isbn}.")
            return

        self.titulo_buscar.setText(row["titulo"])
        self.autor_buscar.setText(row["autor"])
        self.descripcion_buscar.setPlainText(row["descripcion"] or "")
        self.lbl_estado.setText(f"Libro {isbn} cargado.")

    def _accion_modificar(self):
        texto = self.isbn_buscar.text().strip()
        isbn = texto.split(" - ")[0] if " - " in texto else texto

        titulo = self.titulo_buscar.text().strip()
        autor = self.autor_buscar.text().strip()
        descripcion = self.descripcion_buscar.toPlainText().strip()

        if not self._validar_campos(self.isbn_buscar, self.titulo_buscar, self.autor_buscar):
            return

        ok = self.db.editar(isbn, titulo, autor, descripcion)
        if ok:
            self.lbl_estado.setText(f"Libro {isbn} actualizado.")
            self._configurar_autocompletado()
        else:
            QMessageBox.information(self, "Modificar", f"No existe un libro con ISBN {isbn}.")

    def _accion_borrar(self):
        texto = self.isbn_buscar.text().strip()
        isbn = texto.split(" - ")[0] if " - " in texto else texto

        if not isbn:
            QMessageBox.information(self, "Borrar", "Introduce un ISBN para borrar.")
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
            self._configurar_autocompletado()
        else:
            QMessageBox.information(self, "Borrar", f"No existe un libro con ISBN {isbn}.")

    def _accion_consultar(self):
        isbn = self.isbn_consulta.text().strip()
        if not isbn:
            QMessageBox.information(self, "Consulta", "Introduce un ISBN para consultar.")
            return

        row = self.db.consultar(isbn)
        if not row:
            QMessageBox.information(self, "Consulta", f"No existe un libro con ISBN {isbn}.")
            return

        self.titulo_consulta.setText(row["titulo"])
        self.autor_consulta.setText(row["autor"])
        self.descripcion_consulta.setPlainText(row["descripcion"] or "")
        self.lbl_estado.setText(f"Libro {isbn} consultado.")

    def _accion_listar(self):
        dlg = ListadoDialog(self.db, self)
        dlg.exec()


# ---------------------------------------------------------
#   MAIN
# ---------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
