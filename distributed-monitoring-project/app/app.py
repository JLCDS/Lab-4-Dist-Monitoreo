from flask import Flask, jsonify, request, Response, render_template
from prometheus_client import Counter, Histogram, generate_latest
import random
import signal
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
    global service_down, high_latency, error_rate
    
    # Simular caída del servicio
    if service_down:
        return '', 503
    
    start_time = time.time()
    REQUEST_COUNT.labels(method=request.method, endpoint='/api').inc()
    
    # Simular tasa de error
    if random.random() < error_rate:
        REQUEST_LATENCY.labels(endpoint='/api').observe(time.time() - start_time)
        return jsonify({"error": "Internal Server Error"}), 500
    
    # Simular latencia alta
    if high_latency:
        time.sleep(random.uniform(2, 5))
    
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
    
    # Hacer el proceso más pesado para generar más latencia
    total = 0
    for i in range(1, 3000000):  # Aumentado para generar más latencia
        total += (i % 7) * (i % 13)  # Operación más costosa
    
    # Agregar un sleep aleatorio para simular I/O
    time.sleep(random.uniform(0.1, 0.5))
    
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

# Variables globales para simulación
service_down = False
high_latency = False
error_rate = 0

@app.route('/simulate/service-down', methods=['POST'])
def simulate_service_down():
    """Simula una caída del servicio activando/desactivando el flag."""
    global service_down
    data = request.get_json(force=True)
    service_down = data.get('enabled', False)
    if service_down:
        return jsonify({'status': 'Service down simulation enabled'}), 200
    return jsonify({'status': 'Service down simulation disabled'}), 200

@app.route('/simulate/high-latency', methods=['POST'])
def simulate_high_latency():
    """Simula latencia alta activando/desactivando el flag."""
    global high_latency
    data = request.get_json(force=True)
    high_latency = data.get('enabled', False)
    if high_latency:
        return jsonify({'status': 'High latency simulation enabled'}), 200
    return jsonify({'status': 'High latency simulation disabled'}), 200

@app.route('/simulate/error-rate', methods=['POST'])
def simulate_error_rate():
    """Simula una tasa de error específica."""
    global error_rate
    data = request.get_json(force=True)
    error_rate = float(data.get('rate', 0))  # rate debe ser entre 0 y 1
    return jsonify({'status': f'Error rate set to {error_rate}'}), 200


if __name__ == '__main__':
    # Inicializar DB al arrancar
    try:
        init_db()
    except Exception as e:
        print(f"Warning: no se pudo inicializar la BD: {e}")
    app.run(host='0.0.0.0', port=5000, debug=True)
