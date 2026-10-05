from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "biblioteca.db"

#  INICIALIZACIÓN DE BASE DE DATOS

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS autores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            nacionalidad TEXT,
            anio_nacimiento INTEGER
        );

        CREATE TABLE IF NOT EXISTS libros (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo      TEXT    NOT NULL,
            isbn        TEXT    UNIQUE,
            anio        INTEGER,
            genero      TEXT,
            stock       INTEGER NOT NULL DEFAULT 1,
            autor_id    INTEGER NOT NULL,
            FOREIGN KEY (autor_id) REFERENCES autores(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prestamos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            lector      TEXT    NOT NULL,
            libro_id    INTEGER NOT NULL,
            fecha_prestamo TEXT NOT NULL DEFAULT (date('now')),
            fecha_devolucion TEXT,
            devuelto    INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (libro_id) REFERENCES libros(id) ON DELETE CASCADE
        );
    """)

    # Datos de ejemplo
    cur.execute("SELECT COUNT(*) FROM autores")
    if cur.fetchone()[0] == 0:
        cur.executescript("""
            INSERT INTO autores (nombre, nacionalidad, anio_nacimiento) VALUES
                ('Gabriel García Márquez', 'Colombiana', 1927),
                ('Isabel Allende',         'Chilena',    1942),
                ('Jorge Luis Borges',      'Argentina',  1899),
                ('Octavio Paz',            'Mexicana',   1914);

            INSERT INTO libros (titulo, isbn, anio, genero, stock, autor_id) VALUES
                ('Cien años de soledad',       '978-84-397-0038-4', 1967, 'Realismo mágico', 3, 1),
                ('El amor en los tiempos del cólera', '978-84-397-0039-1', 1985, 'Novela', 2, 1),
                ('La casa de los espíritus',   '978-84-397-0100-8', 1982, 'Realismo mágico', 2, 2),
                ('Ficciones',                  '978-84-397-0200-5', 1944, 'Cuentos',          4, 3),
                ('El laberinto de la soledad', '978-84-397-0300-2', 1950, 'Ensayo',           1, 4);

            INSERT INTO prestamos (lector, libro_id, fecha_prestamo, devuelto) VALUES
                ('Ana López',    1, '2025-04-01', 0),
                ('Carlos Ruiz',  3, '2025-04-10', 1),
                ('María Torres', 4, '2025-05-01', 0);
        """)

    conn.commit()
    conn.close()

#  INTERFAZ WEB

@app.route("/")
def index():
    return render_template("index.html")

#  CRUD AUTORES

@app.route("/autores", methods=["GET"])
def get_autores():
    try:
        conn = get_db()
        autores = conn.execute("SELECT * FROM autores ORDER BY nombre").fetchall()
        conn.close()
        return jsonify([dict(a) for a in autores])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/autores/<int:id>", methods=["GET"])
def get_autor(id):
    try:
        conn = get_db()
        autor = conn.execute("SELECT * FROM autores WHERE id = ?", (id,)).fetchone()
        conn.close()
        if not autor:
            return jsonify({"error": "Autor no encontrado"}), 404
        return jsonify(dict(autor))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/autores", methods=["POST"])
def create_autor():
    try:
        data = request.json
        if not data or "nombre" not in data:
            return jsonify({"error": "El campo 'nombre' es obligatorio"}), 400
        if len(data["nombre"].strip()) < 2:
            return jsonify({"error": "El nombre debe tener al menos 2 caracteres"}), 400

        conn = get_db()
        cur = conn.execute(
            "INSERT INTO autores (nombre, nacionalidad, anio_nacimiento) VALUES (?, ?, ?)",
            (data["nombre"].strip(), data.get("nacionalidad"), data.get("anio_nacimiento"))
        )
        conn.commit()
        nuevo_id = cur.lastrowid
        autor = conn.execute("SELECT * FROM autores WHERE id = ?", (nuevo_id,)).fetchone()
        conn.close()
        return jsonify(dict(autor)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/autores/<int:id>", methods=["PUT"])
def update_autor(id):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400

        conn = get_db()
        autor = conn.execute("SELECT * FROM autores WHERE id = ?", (id,)).fetchone()
        if not autor:
            conn.close()
            return jsonify({"error": "Autor no encontrado"}), 404

        autor = dict(autor)
        nombre = data.get("nombre", autor["nombre"]).strip()
        if len(nombre) < 2:
            conn.close()
            return jsonify({"error": "El nombre debe tener al menos 2 caracteres"}), 400

        conn.execute(
            "UPDATE autores SET nombre=?, nacionalidad=?, anio_nacimiento=? WHERE id=?",
            (nombre, data.get("nacionalidad", autor["nacionalidad"]),
             data.get("anio_nacimiento", autor["anio_nacimiento"]), id)
        )
        conn.commit()
        autor_actualizado = conn.execute("SELECT * FROM autores WHERE id = ?", (id,)).fetchone()
        conn.close()
        return jsonify(dict(autor_actualizado))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/autores/<int:id>", methods=["DELETE"])
def delete_autor(id):
    try:
        conn = get_db()
        autor = conn.execute("SELECT * FROM autores WHERE id = ?", (id,)).fetchone()
        if not autor:
            conn.close()
            return jsonify({"error": "Autor no encontrado"}), 404
        conn.execute("DELETE FROM autores WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": f"Autor '{autor['nombre']}' eliminado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#  CRUD LIBROS

@app.route("/libros", methods=["GET"])
def get_libros():
    try:
        conn = get_db()
        libros = conn.execute("""
            SELECT l.*, a.nombre AS autor_nombre
            FROM libros l
            JOIN autores a ON l.autor_id = a.id
            ORDER BY l.titulo
        """).fetchall()
        conn.close()
        return jsonify([dict(l) for l in libros])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/libros/<int:id>", methods=["GET"])
def get_libro(id):
    try:
        conn = get_db()
        libro = conn.execute("""
            SELECT l.*, a.nombre AS autor_nombre
            FROM libros l JOIN autores a ON l.autor_id = a.id
            WHERE l.id = ?
        """, (id,)).fetchone()
        conn.close()
        if not libro:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify(dict(libro))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/libros", methods=["POST"])
def create_libro():
    try:
        data = request.json
        errores = []
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400
        if "titulo" not in data or not data["titulo"].strip():
            errores.append("El campo 'titulo' es obligatorio")
        if "autor_id" not in data:
            errores.append("El campo 'autor_id' es obligatorio")
        if errores:
            return jsonify({"error": errores}), 400

        stock = data.get("stock", 1)
        if not isinstance(stock, int) or stock < 0:
            return jsonify({"error": "El stock debe ser un número entero positivo"}), 400

        conn = get_db()
        autor = conn.execute("SELECT id FROM autores WHERE id = ?", (data["autor_id"],)).fetchone()
        if not autor:
            conn.close()
            return jsonify({"error": "El autor_id no existe"}), 400

        cur = conn.execute(
            "INSERT INTO libros (titulo, isbn, anio, genero, stock, autor_id) VALUES (?,?,?,?,?,?)",
            (data["titulo"].strip(), data.get("isbn"), data.get("anio"),
             data.get("genero"), stock, data["autor_id"])
        )
        conn.commit()
        nuevo_id = cur.lastrowid
        libro = conn.execute("""
            SELECT l.*, a.nombre AS autor_nombre FROM libros l
            JOIN autores a ON l.autor_id = a.id WHERE l.id = ?
        """, (nuevo_id,)).fetchone()
        conn.close()
        return jsonify(dict(libro)), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "El ISBN ya existe en la base de datos"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/libros/<int:id>", methods=["PUT"])
def update_libro(id):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400

        conn = get_db()
        libro = conn.execute("SELECT * FROM libros WHERE id = ?", (id,)).fetchone()
        if not libro:
            conn.close()
            return jsonify({"error": "Libro no encontrado"}), 404

        libro = dict(libro)
        titulo = data.get("titulo", libro["titulo"]).strip()
        if not titulo:
            conn.close()
            return jsonify({"error": "El título no puede estar vacío"}), 400

        stock = data.get("stock", libro["stock"])
        if not isinstance(stock, int) or stock < 0:
            conn.close()
            return jsonify({"error": "El stock debe ser un número entero positivo"}), 400

        autor_id = data.get("autor_id", libro["autor_id"])
        if autor_id != libro["autor_id"]:
            autor = conn.execute("SELECT id FROM autores WHERE id = ?", (autor_id,)).fetchone()
            if not autor:
                conn.close()
                return jsonify({"error": "El autor_id no existe"}), 400

        conn.execute(
            "UPDATE libros SET titulo=?, isbn=?, anio=?, genero=?, stock=?, autor_id=? WHERE id=?",
            (titulo, data.get("isbn", libro["isbn"]), data.get("anio", libro["anio"]),
             data.get("genero", libro["genero"]), stock, autor_id, id)
        )
        conn.commit()
        libro_actualizado = conn.execute("""
            SELECT l.*, a.nombre AS autor_nombre FROM libros l
            JOIN autores a ON l.autor_id = a.id WHERE l.id = ?
        """, (id,)).fetchone()
        conn.close()
        return jsonify(dict(libro_actualizado))
    except sqlite3.IntegrityError:
        return jsonify({"error": "El ISBN ya existe en la base de datos"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/libros/<int:id>", methods=["DELETE"])
def delete_libro(id):
    try:
        conn = get_db()
        libro = conn.execute("SELECT * FROM libros WHERE id = ?", (id,)).fetchone()
        if not libro:
            conn.close()
            return jsonify({"error": "Libro no encontrado"}), 404
        conn.execute("DELETE FROM libros WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": f"Libro '{libro['titulo']}' eliminado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#  CRUD PRÉSTAMOS

@app.route("/prestamos", methods=["GET"])
def get_prestamos():
    try:
        conn = get_db()
        prestamos = conn.execute("""
            SELECT p.*, l.titulo AS libro_titulo
            FROM prestamos p
            JOIN libros l ON p.libro_id = l.id
            ORDER BY p.fecha_prestamo DESC
        """).fetchall()
        conn.close()
        return jsonify([dict(p) for p in prestamos])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/prestamos/<int:id>", methods=["GET"])
def get_prestamo(id):
    try:
        conn = get_db()
        prestamo = conn.execute("""
            SELECT p.*, l.titulo AS libro_titulo FROM prestamos p
            JOIN libros l ON p.libro_id = l.id WHERE p.id = ?
        """, (id,)).fetchone()
        conn.close()
        if not prestamo:
            return jsonify({"error": "Préstamo no encontrado"}), 404
        return jsonify(dict(prestamo))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/prestamos", methods=["POST"])
def create_prestamo():
    try:
        data = request.json
        errores = []
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400
        if "lector" not in data or not data["lector"].strip():
            errores.append("El campo 'lector' es obligatorio")
        if "libro_id" not in data:
            errores.append("El campo 'libro_id' es obligatorio")
        if errores:
            return jsonify({"error": errores}), 400

        conn = get_db()
        libro = conn.execute("SELECT * FROM libros WHERE id = ?", (data["libro_id"],)).fetchone()
        if not libro:
            conn.close()
            return jsonify({"error": "El libro_id no existe"}), 400
        if libro["stock"] < 1:
            conn.close()
            return jsonify({"error": "No hay ejemplares disponibles de este libro"}), 400

        cur = conn.execute(
            "INSERT INTO prestamos (lector, libro_id, fecha_prestamo) VALUES (?, ?, date('now'))",
            (data["lector"].strip(), data["libro_id"])
        )
        conn.execute("UPDATE libros SET stock = stock - 1 WHERE id = ?", (data["libro_id"],))
        conn.commit()
        nuevo_id = cur.lastrowid
        prestamo = conn.execute("""
            SELECT p.*, l.titulo AS libro_titulo FROM prestamos p
            JOIN libros l ON p.libro_id = l.id WHERE p.id = ?
        """, (nuevo_id,)).fetchone()
        conn.close()
        return jsonify(dict(prestamo)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/prestamos/<int:id>", methods=["PUT"])
def update_prestamo(id):
    """Actualizar préstamo (marcar devuelto, cambiar lector, etc.)"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400

        conn = get_db()
        prestamo = conn.execute("SELECT * FROM prestamos WHERE id = ?", (id,)).fetchone()
        if not prestamo:
            conn.close()
            return jsonify({"error": "Préstamo no encontrado"}), 404

        prestamo = dict(prestamo)
        devuelto_anterior = prestamo["devuelto"]
        devuelto_nuevo = data.get("devuelto", devuelto_anterior)

        # Si se devuelve, reponer stock
        if devuelto_nuevo == 1 and devuelto_anterior == 0:
            conn.execute("UPDATE libros SET stock = stock + 1 WHERE id = ?", (prestamo["libro_id"],))
            conn.execute(
                "UPDATE prestamos SET devuelto=1, fecha_devolucion=date('now'), lector=? WHERE id=?",
                (data.get("lector", prestamo["lector"]), id)
            )
        else:
            conn.execute(
                "UPDATE prestamos SET lector=?, devuelto=? WHERE id=?",
                (data.get("lector", prestamo["lector"]), devuelto_nuevo, id)
            )

        conn.commit()
        prestamo_actualizado = conn.execute("""
            SELECT p.*, l.titulo AS libro_titulo FROM prestamos p
            JOIN libros l ON p.libro_id = l.id WHERE p.id = ?
        """, (id,)).fetchone()
        conn.close()
        return jsonify(dict(prestamo_actualizado))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/prestamos/<int:id>", methods=["DELETE"])
def delete_prestamo(id):
    try:
        conn = get_db()
        prestamo = conn.execute("SELECT * FROM prestamos WHERE id = ?", (id,)).fetchone()
        if not prestamo:
            conn.close()
            return jsonify({"error": "Préstamo no encontrado"}), 404

        # Si no había sido devuelto, reponer stock
        if prestamo["devuelto"] == 0:
            conn.execute("UPDATE libros SET stock = stock + 1 WHERE id = ?", (prestamo["libro_id"],))

        conn.execute("DELETE FROM prestamos WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Préstamo eliminado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
