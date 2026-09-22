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

### Detener Docker Compose

Si ejecutaste el servicio en primer plano con `docker compose up --build`, presiona:

```text
Ctrl + C
```

Esto detiene el proceso que muestra los logs. Para detener y eliminar el contenedor de forma explícita, ejecuta desde otra terminal o después de volver al prompt:

```bash
docker compose down
```

Si lo levantaste en segundo plano con `-d`, no necesitas `Ctrl + C`; basta con ejecutar:

```bash
docker compose down
```

Este comando detiene y elimina los contenedores creados por Compose. La imagen no se elimina y podrá reutilizarse en el siguiente arranque.

Para ejecutarlo en segundo plano:

```bash
docker compose up --build -d
```

Para consultar los logs:

```bash
docker compose logs -f
```

### Administrar el contenedor directamente

También puedes administrar el contenedor usando su ID o nombre. Sustituye
`a842945e2414` por el valor que aparezca en `docker ps`:

```bash
docker ps
```

Detenerlo de forma normal envía `SIGTERM` y permite que la aplicación cierre
correctamente:

```bash
docker stop a842945e2414
```

Forzar su detención envía `SIGKILL`. Úsalo solo si `docker stop` no responde:

```bash
docker kill a842945e2414
```

Reiniciar el contenedor:

```bash
docker restart a842945e2414
```

Eliminar un contenedor detenido:

```bash
docker rm a842945e2414
```

Para servicios iniciados con Docker Compose, `docker compose down` sigue siendo
la opción recomendada porque detiene y elimina los recursos del proyecto de
forma coordinada.

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

### Detener la ejecución de Python

Si arrancaste la aplicación con `python app.py`, mantén enfocada la terminal donde está ejecutándose y presiona:

```text
Ctrl + C
```

Python recibirá la señal de interrupción y el servidor Flask se cerrará. Después puedes salir del entorno virtual con:

```bash
deactivate
```

`deactivate` solo desactiva el entorno virtual; no es necesario para detener el servidor.

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
