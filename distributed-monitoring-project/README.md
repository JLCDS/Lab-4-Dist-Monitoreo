# Biblioteca Flask + MySQL + Prometheus + Grafana

## Descripción

Aplicación web de biblioteca con interfaz gráfica, API REST y monitoreo con Prometheus y Grafana. Permite agregar, buscar y eliminar libros, simular cargas y errores para pruebas de monitoreo.

## Estructura del proyecto

```
distributed-monitoring-project/
│
├── app/
│   ├── app.py                # Código principal Flask
│   ├── requirements.txt      # Dependencias Python
│   ├── Dockerfile            # Imagen de la app
│   ├── templates/
│   │   └── index.html        # Interfaz web
│   └── static/
│       └── styles.css        # Estilos CSS
│
├── db/
│   └── init.sql              # Script para crear BD y tabla
│
├── monitoring/
│   ├── prometheus.yml        # Configuración Prometheus
│   ├── alert_rules.yml       # (opcional) reglas de alerta
│   └── alertmanager.yml      # (opcional) alertmanager
│
├── docker-compose.yml        # Orquestación de servicios
└── READMEE.md                # Manual y notas
```

## Requisitos

- Docker y Docker Compose instalados
- (Opcional) Python 3.9+ y pip para pruebas locales

## Instalación y ejecución

1. Clona el repositorio:
   ```bash
   git clone <URL_DEL_REPO>
   cd distributed-monitoring-project
   ```

2. Levanta todos los servicios con Docker Compose:
   ```powershell
   docker-compose up --build
   ```
   (Usa `docker-compose up -d --build` para modo background)

3. Accede a los servicios:
   - App Flask: [http://localhost:5000](http://localhost:5000)
   - Prometheus: [http://localhost:9090](http://localhost:9090)
   - Grafana: [http://localhost:3012](http://localhost:3012) (usuario: admin, contraseña: admin)
   - MySQL: puerto 3307 (usuario: root, contraseña: example)

## Funcionalidades

- **Agregar libro:** Completa el formulario y pulsa “Crear”.
- **Buscar libro:** Escribe título o autor y pulsa “Buscar”.
- **Eliminar libro:** Pulsa “Eliminar” junto al libro.
- **Refrescar:** Actualiza la lista de libros.
- **Simular carga:** Pulsa “Solicitud pesada (/heavy)” para generar latencia.
- **Simular error:** Pulsa “Forzar error (/error)” para generar errores 500.

## Monitoreo

- **Métricas Prometheus:** [http://localhost:5000/metrics](http://localhost:5000/metrics)
- **Prometheus:** Consulta métricas como `app_request_total` y `app_request_latency_seconds`.
- **Grafana:** Crea dashboards usando Prometheus como fuente de datos.

## Pruebas con curl/Postman

```bash
# Agregar libro
curl -X POST http://localhost:5000/books -H "Content-Type: application/json" -d '{"title":"Nuevo libro","author":"Autor"}'

# Listar libros
curl http://localhost:5000/books

# Simular carga
curl http://localhost:5000/heavy

# Simular error
curl http://localhost:5000/error
```

## Balanceador de carga (Nginx)

Este proyecto incluye un balanceador de carga simple basado en Nginx que distribuye el tráfico entre dos réplicas de la aplicación (`app1` y `app2`). Se expone en el host por el puerto 5000 y hace proxy a las aplicaciones internas en su puerto 5000.

Puntos importantes:
- El balanceador escucha en: http://localhost:5000
- Réplicas internas: `app1:5000` y `app2:5000` (no están mapeadas al host)
- Base de datos compartida: el contenedor `db` (MySQL) es accesible por ambas réplicas. En el host está mapeado en el puerto 3307 (host -> container 3306).

Comandos para probar el balanceador

PowerShell (repetir varias veces para ver distribución round-robin):
```powershell
# Ver la réplica que atendió (whoami)
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:5000/whoami | Select-Object -ExpandProperty Content

# Crear un libro a través del balanceador
$body = @{ title = 'Mi libro'; author = 'Yo' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/books -Method Post -Body $body -ContentType 'application/json'

# Listar libros
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:5000/books | Select-Object -ExpandProperty Content
```

curl (Linux/macOS / Git Bash):
```bash
# whoami (ver qué réplica atiende)
curl -sS http://localhost:5000/whoami

# crear libro
curl -sS -X POST -H "Content-Type: application/json" -d '{"title":"Mi libro","author":"Yo"}' http://localhost:5000/books

# listar libros
curl -sS http://localhost:5000/books
```

Notas de comportamiento y recomendaciones
- Nginx por defecto usa round-robin para distribuir tráfico. En pruebas rápidas la conexión TCP puede reutilizarse y parecer que una sola réplica atiende muchas peticiones; hemos añadido en la configuración actual cabeceras para cerrar la conexión upstream por petición y hacer la distribución más visible en pruebas.
- Prometheus scrapea actualmente ambas réplicas individualmente y también el endpoint del balanceador. Ajusta `monitoring/prometheus.yml` si quieres solo métricas agregadas a nivel de Nginx.


## Notas

- Si cambias `requirements.txt`, reconstruye la imagen:
  ```powershell
  docker-compose up --build
  ```
- Si la base de datos no se inicializa, elimina los volúmenes de Docker y vuelve a levantar:
  ```powershell
  docker-compose down -v
  docker-compose up --build
  ```
