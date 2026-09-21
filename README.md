# TicketFlow

Aplicación web para generar tickets de mesa de ayuda de forma rápida y clara. Permite registrar el solicitante, correo electrónico, categoría, prioridad, asunto y descripción. Al enviar el formulario, genera un identificador único y muestra una vista previa lista para compartir.

## Funcionalidades

- Formulario responsive en español.
- Categorías: soporte, acceso y cuentas, hardware, software, redes y otros.
- Niveles de prioridad: baja, media, alta y crítica.
- Identificador automático con formato `TCK-YYYYMMDD-XXXX`.
- Vista previa del ticket generado.
- Copia del resumen al portapapeles.
- Servidor de producción con Gunicorn.
- Despliegue reproducible mediante Docker Compose.

## Requisitos

Para ejecutar con Docker:

- Docker Engine.
- Docker Compose v2 (`docker compose`).

Para ejecutar sin Docker:

- Python 3.11 o superior.
- `pip`.

## Ejecutar con Docker

Construye la imagen y levanta el servicio:

```bash
docker compose up --build
```

Abre [http://localhost:5000](http://localhost:5000) en el navegador.

Para detener y eliminar el contenedor:

```bash
docker compose down
```

Para ejecutarlo en segundo plano:

```bash
docker compose up --build -d
```

Para consultar los logs:

```bash
docker compose logs -f
```

## Ejecutar localmente

Crear y activar un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instalar dependencias y arrancar:

```bash
pip install -r requirements.txt
python app.py
```

La aplicación escucha en `http://localhost:5000`.

## Configuración

El puerto expuesto por Docker se define en `docker-compose.yml`:

```yaml
ports:
  - "5000:5000"
```

Por ejemplo, para acceder desde el puerto `8080` del equipo host:

```yaml
ports:
  - "8080:5000"
```

El servidor interno permanece escuchando en el puerto `5000`.

## Estructura del proyecto

```text
.
├── app.py                 # Rutas Flask y generación del ticket
├── templates/index.html   # Formulario y vista previa
├── static/style.css       # Estilos responsive
├── Dockerfile             # Imagen de producción
├── docker-compose.yml     # Servicio y publicación del puerto
└── requirements.txt       # Dependencias Python
```

## Limitaciones actuales

Los tickets se generan en memoria y no se guardan en una base de datos. Al reiniciar el contenedor se pierde la información. La persistencia, autenticación y gestión histórica de tickets pueden incorporarse en una siguiente iteración.

## Licencia

Consulta el archivo [LICENSE](LICENSE) para conocer los términos de uso.
