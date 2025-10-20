from flask import Flask, jsonify, request, Response, render_template
from prometheus_client import Counter, Histogram, generate_latest
import time
import os
import pymysql
import socket

app = Flask(__name__)

# ───── METRICAS PROMETHEUS ─────

REQUEST_COUNT = Counter(
    'app_request_total',
    'Total de peticiones recibidas',
    ['method', 'endpoint']
)

REQUEST_LATENCY = Histogram(
    'app_request_latency_seconds',
    'Latencia de las peticiones',
    ['endpoint']
)


# ───── CONFIG DB ─────
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')
DB_NAME = os.environ.get('DB_NAME', 'books_db')


def get_db_connection():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASSWORD, database=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor, autocommit=True)


def init_db():
    # Conectar al servidor sin seleccionar BD para crearla si no existe
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASSWORD, cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    conn.close()

    # Crear tabla si no existe
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB;
            """
        )
    conn.close()


# ───── RUTA FRONTEND ─────
@app.route('/')
def home_page():
    return render_template("index.html")


# ───── RUTAS DE API ─────
@app.route('/api')
def api_home():
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/api').inc()
    response = jsonify({"message": "API funcionando correctamente"})
    REQUEST_LATENCY.labels(endpoint='/api').observe(time.time() - start_time)
    return response, 200


@app.route('/books', methods=['GET', 'POST'])
def books():
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/books').inc()

    if request.method == 'POST':
        try:
            data = request.get_json(force=True) or {}
            title = data.get('title')
            author = data.get('author')
            if not title or not author:
                return jsonify({'error': 'title and author are required'}), 400
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO books (title, author) VALUES (%s, %s)", (title, author))
                book_id = cur.lastrowid
            conn.close()
            REQUEST_LATENCY.labels(endpoint='/books').observe(time.time() - start_time)
            return jsonify({'id': book_id, 'title': title, 'author': author}), 201
        except Exception as e:
            print(f"Error en POST /books: {e}")
            return jsonify({'error': str(e)}), 500

    # GET
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, author FROM books ORDER BY id ASC")
        rows = cur.fetchall()
    conn.close()

    REQUEST_LATENCY.labels(endpoint='/books').observe(time.time() - start_time)
    return jsonify(rows), 200


@app.route('/books/<int:book_id>', methods=['GET', 'DELETE'])
def book_by_id(book_id):
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/books/<id>').inc()
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, author FROM books WHERE id=%s", (book_id,))
        row = cur.fetchone()
        if request.method == 'DELETE':
            if row is None:
                conn.close()
                REQUEST_LATENCY.labels(endpoint='/books/<id>').observe(time.time() - start_time)
                return jsonify({'error': 'not found'}), 404
            cur.execute("DELETE FROM books WHERE id=%s", (book_id,))
            conn.close()
            REQUEST_LATENCY.labels(endpoint='/books/<id>').observe(time.time() - start_time)
            return '', 204
    conn.close()
    if row is None:
        REQUEST_LATENCY.labels(endpoint='/books/<id>').observe(time.time() - start_time)
        return jsonify({'error': 'not found'}), 404
    REQUEST_LATENCY.labels(endpoint='/books/<id>').observe(time.time() - start_time)
    return jsonify(row), 200


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/search').inc()
    conn = get_db_connection()
    with conn.cursor() as cur:
        if q == '':
            cur.execute("SELECT id, title, author FROM books ORDER BY id ASC")
        else:
            like = f"%{q}%"
            cur.execute("SELECT id, title, author FROM books WHERE title LIKE %s OR author LIKE %s ORDER BY id ASC", (like, like))
        rows = cur.fetchall()
    conn.close()
    REQUEST_LATENCY.labels(endpoint='/search').observe(time.time() - start_time)
    return jsonify(rows), 200


@app.route('/heavy')
def heavy():
    # Simula una operación pesada para generar latencia
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/heavy').inc()
    # hacer cálculos intensivos (CPU bound) o sleep para I/O
    total = 0
    for i in range(1, 2000000):
        total += i % 7
    REQUEST_LATENCY.labels(endpoint='/heavy').observe(time.time() - start_time)
    return jsonify({'status': 'done', 'work': total}), 200


@app.route('/error')
def error():
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/error').inc()
    try:
        raise RuntimeError('Simulated error for testing')
    except Exception:
        REQUEST_LATENCY.labels(endpoint='/error').observe(time.time() - start_time)
        return jsonify({'error': 'internal server error'}), 500


# ───── MÉTRICAS ─────
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


@app.route('/whoami')
def whoami():
    """Devuelve el hostname del contenedor para verificar qué réplica respondió."""
    try:
        host = socket.gethostname()
    except Exception:
        host = 'unknown'
    return jsonify({'whoami': host}), 200


if __name__ == '__main__':
    # Inicializar DB al arrancar
    try:
        init_db()
    except Exception as e:
        print(f"Warning: no se pudo inicializar la BD: {e}")
    app.run(host='0.0.0.0', port=5000, debug=True)
