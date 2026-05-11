import random
import sqlite3
from pathlib import Path

from faker import Faker

DB_PATH = Path("libros.db")


def crear_tabla(conn: sqlite3.Connection):
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS libros (
                isbn TEXT PRIMARY KEY,
                titulo TEXT NOT NULL,
                autor TEXT NOT NULL,
                descripcion TEXT
            )
            """
        )


def poblar_libros(cantidad: int = 100):
    fake = Faker("es_ES")
    conn = sqlite3.connect(DB_PATH)
    crear_tabla(conn)

    insertados = 0
    intentos = 0

    while insertados < cantidad and intentos < cantidad * 5:
        intentos += 1
        isbn = fake.unique.isbn13(separator="")
        titulo = fake.sentence(nb_words=random.randint(2, 6)).rstrip(".")
        autor = fake.name()
        descripcion = fake.paragraph(nb_sentences=3)

        try:
            with conn:
                conn.execute(
                    "INSERT INTO libros(isbn, titulo, autor, descripcion) VALUES(?, ?, ?, ?)",
                    (isbn, titulo, autor, descripcion),
                )
            insertados += 1
        except sqlite3.IntegrityError:
            pass

    conn.close()
    print(f"Insertados {insertados} libros en {DB_PATH}.")


if __name__ == "__main__":
    print("=== Generador de libros ===")
    while True:
        entrada = input("¿Cuántos libros quieres generar? (ej: 100): ").strip()
        if entrada.isdigit() and int(entrada) > 0:
            cantidad = int(entrada)
            break
        print("⚠️  Por favor, introduce un número válido mayor que 0.")

    poblar_libros(cantidad)
