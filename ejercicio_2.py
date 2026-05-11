import sqlite3
import sys
from math import ceil
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
    QStyle,
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
        self.resize(1000, 650)

        self.page_size = 20
        self.current_page = 0
        self._all_rows = []

        self._init_ui()
        self._apply_styles()
        self._recargar_tabla()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- Formulario ---
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

        # --- Botones de acciones ---
        btn_grid = QGridLayout()
        style = self.style()

        self.btn_nuevo = QPushButton("Crear libro")
        self.btn_nuevo.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))

        self.btn_guardar = QPushButton("Guardar libro")
        self.btn_guardar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))

        self.btn_consulta = QPushButton("Buscar libro")
        self.btn_consulta.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))

        self.btn_editar = QPushButton("Actualizar libro")
        self.btn_editar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))

        self.btn_borrar = QPushButton("Eliminar libro")
        self.btn_borrar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

        self.btn_listado = QPushButton("Mostrar todos los libros")
        self.btn_listado.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))

        self.btn_limpiar = QPushButton("Limpiar campos")
        self.btn_limpiar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))

        self.btn_salir = QPushButton("Cerrar aplicación")
        self.btn_salir.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))

        btn_grid.addWidget(self.btn_nuevo, 0, 0)
        btn_grid.addWidget(self.btn_guardar, 0, 1)
        btn_grid.addWidget(self.btn_consulta, 0, 2)
        btn_grid.addWidget(self.btn_editar, 1, 0)
        btn_grid.addWidget(self.btn_borrar, 1, 1)
        btn_grid.addWidget(self.btn_listado, 1, 2)
        btn_grid.addWidget(self.btn_limpiar, 2, 0, 1, 3)

        top_layout = QVBoxLayout()
        top_layout.addWidget(form_box)
        top_layout.addLayout(btn_grid)

        # --- Buscador global ---
        search_box = QGroupBox("Búsqueda")
        search_layout = QHBoxLayout(search_box)
        self.search_global = QLineEdit()
        self.search_global.setPlaceholderText("Buscar por título o autor...")
        search_layout.addWidget(QLabel("Filtro:"))
        search_layout.addWidget(self.search_global)

        # --- Tabla ---
        table_box = QGroupBox("Listado de libros")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ISBN", "Título", "Autor", "Descripción"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._cargar_seleccion_a_form)
        table_layout.addWidget(self.table)

        # --- Paginación + estado + salir ---
        footer = QHBoxLayout()
        self.lbl_estado = QLabel("Listo")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.btn_prev_page = QPushButton("◀ Anterior")
        self.btn_next_page = QPushButton("Siguiente ▶")
        self.lbl_paginacion = QLabel("Página 1/1")

        footer.addWidget(self.lbl_estado)
        footer.addStretch()
        footer.addWidget(self.btn_prev_page)
        footer.addWidget(self.btn_next_page)
        footer.addWidget(self.lbl_paginacion)
        footer.addSpacing(20)
        footer.addWidget(self.btn_salir)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(search_box)
        main_layout.addWidget(table_box)
        main_layout.addLayout(footer)

        # --- Conexiones ---
        self.btn_nuevo.clicked.connect(self._accion_nuevo)
        self.btn_guardar.clicked.connect(self._accion_guardar)
        self.btn_consulta.clicked.connect(self._accion_consulta)
        self.btn_editar.clicked.connect(self._accion_editar)
        self.btn_borrar.clicked.connect(self._accion_borrar)
        self.btn_listado.clicked.connect(self._recargar_tabla)
        self.btn_limpiar.clicked.connect(self._limpiar_form)
        self.btn_salir.clicked.connect(self.close)

        self.search_global.textChanged.connect(self._aplicar_filtro_y_paginacion)
        self.btn_prev_page.clicked.connect(self._pagina_anterior)
        self.btn_next_page.clicked.connect(self._pagina_siguiente)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
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
            QPushButton:disabled {
                background-color: #9CA3AF;
            }
            QLineEdit, QPlainTextEdit {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 4px;
            }
            QTableWidget {
                gridline-color: #D1D5DB;
                alternate-background-color: #F9FAFB;
            }
            QHeaderView::section {
                background-color: #E5E7EB;
                padding: 4px;
                border: 1px solid #D1D5DB;
            }
            """
        )

    def _valores_form(self):
        return (
            self.isbn_input.text().strip(),
            self.titulo_input.text().strip(),
            self.autor_input.text().strip(),
            self.descripcion_input.toPlainText().strip(),
        )

    def _reset_validacion(self):
        for widget in (self.isbn_input, self.titulo_input, self.autor_input):
            widget.setStyleSheet("")

    def _validar_para_guardar(self):
        self._reset_validacion()
        isbn, titulo, autor, _ = self._valores_form()
        ok = True
        if not isbn:
            self.isbn_input.setStyleSheet("border: 2px solid #DC2626;")
            ok = False
        if not titulo:
            self.titulo_input.setStyleSheet("border: 2px solid #DC2626;")
            ok = False
        if not autor:
            self.autor_input.setStyleSheet("border: 2px solid #DC2626;")
            ok = False
        if not ok:
            QMessageBox.warning(self, "Campos obligatorios", "ISBN, título y autor son obligatorios.")
        return ok

    # --- Acciones ---

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

    def _accion_guardar(self):
        if not self._validar_para_guardar():
            return
        isbn, titulo, autor, descripcion = self._valores_form()
        existente = self.db.consultar(isbn)
        if existente:
            ok = self.db.editar(isbn, titulo, autor, descripcion)
            if ok:
                self.lbl_estado.setText(f"Libro {isbn} actualizado (guardar).")
        else:
            try:
                self.db.nuevo_libro(isbn, titulo, autor, descripcion)
                self.lbl_estado.setText(f"Libro {isbn} creado (guardar).")
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Error", "No se ha podido guardar el libro.")
        self._recargar_tabla()

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

    # --- Listado, filtro y paginación ---

    def _recargar_tabla(self):
        self._all_rows = list(self.db.listado())
        self.current_page = 0
        self._aplicar_filtro_y_paginacion()
        self.lbl_estado.setText(f"Listado actualizado ({len(self._all_rows)} libros).")

    def _aplicar_filtro_y_paginacion(self):
        filtro = self.search_global.text().strip().lower()
        if filtro:
            filtered = [
                row
                for row in self._all_rows
                if filtro in (row["titulo"] or "").lower()
                or filtro in (row["autor"] or "").lower()
            ]
            self._poblar_tabla(filtered)
            self.lbl_paginacion.setText(f"Filtrados: {len(filtered)}")
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
        else:
            total = len(self._all_rows)
            if total == 0:
                self._poblar_tabla([])
                self.lbl_paginacion.setText("Página 0/0")
                self.btn_prev_page.setEnabled(False)
                self.btn_next_page.setEnabled(False)
                return

            total_pages = ceil(total / self.page_size)
            self.current_page = max(0, min(self.current_page, total_pages - 1))
            start = self.current_page * self.page_size
            end = start + self.page_size
            page_rows = self._all_rows[start:end]
            self._poblar_tabla(page_rows)

            self.lbl_paginacion.setText(
                f"Página {self.current_page + 1}/{total_pages} ({total} libros)"
            )
            self.btn_prev_page.setEnabled(self.current_page > 0)
            self.btn_next_page.setEnabled(self.current_page < total_pages - 1)

    def _poblar_tabla(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["isbn"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["titulo"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["autor"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["descripcion"] or ""))
        self.table.resizeColumnsToContents()

    def _pagina_anterior(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._aplicar_filtro_y_paginacion()

    def _pagina_siguiente(self):
        self.current_page += 1
        self._aplicar_filtro_y_paginacion()

    # --- Utilidades UI ---

    def _limpiar_form(self):
        self.isbn_input.clear()
        self.titulo_input.clear()
        self.autor_input.clear()
        self.descripcion_input.clear()
        self._reset_validacion()

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
