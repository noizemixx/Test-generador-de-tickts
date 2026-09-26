# TicketFlow

Aplicación web para generar tickets de mesa de ayuda de forma rápida y clara. Permite registrar el solicitante, correo electrónico, categoría, prioridad, asunto y descripción. Al enviar el formulario, genera un identificador único y muestra una vista previa lista para compartir.

## Funcionalidades

- Formulario responsive en español.
- Categorías: soporte, acceso y cuentas, hardware, software, redes y otros.
- Niveles de prioridad: baja, media, alta y crítica.
- Identificador automático con formato `TCK-YYYYMMDD-000001`.
- Almacenamiento persistente de tickets en SQLite.
- Edición de tickets con una nueva versión por cada guardado.
- Consulta del detalle e historial completo, incluyendo la versión inicial.
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
Los tickets se guardan en el volumen Docker `ticketflow_data`, por lo que siguen disponibles al detener o recrear el contenedor.

> **Importante:** `docker compose down -v` también elimina el volumen y borra todos los tickets guardados.

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
En ejecución local, la base de datos se crea en `instance/ticketflow.sqlite3`. Puedes cambiar su ubicación definiendo la variable de entorno `TICKETFLOW_DB`.

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
├── app.py                 # Rutas Flask, SQLite y versiones
├── templates/             # Formularios, tickets e historial
├── static/style.css       # Estilos responsive
├── Dockerfile             # Imagen de producción
├── docker-compose.yml     # Servicio, puerto y volumen persistente
└── requirements.txt       # Dependencias Python
```

## Ejecutar las pruebas

El proyecto incluye pruebas de creación, edición, persistencia e historial. Instala pytest y ejecútalas:

```bash
python -m pip install pytest
python -m pytest
```

## Control de versiones con Git

Clona el repositorio y entra en la carpeta del proyecto:

```bash
git clone https://github.com/noizemixx/Test-generador-de-tickts.git
cd Test-generador-de-tickts
```

Para trabajar en un cambio, crea una rama propia:

```bash
git switch -c feature/nombre-del-cambio
```

Después de editar, revisa los archivos modificados, prepara los cambios y crea un commit:

```bash
git status
git add README.md app.py
git commit -m "Describe el cambio"
```

Publica la rama en GitHub:

```bash
git push -u origin feature/nombre-del-cambio
```

Abre un Pull Request de esa rama hacia `main`. Para incorporar cambios recientes de `main` a tu rama:

```bash
git fetch origin
git merge origin/main
```

La base SQLite y los archivos de instancia están excluidos de Git; los datos locales de tickets no se suben al repositorio.

## Almacenamiento y limitaciones

Los tickets actuales y todas sus versiones se almacenan en SQLite. Las versiones anteriores no se sobrescriben: al editar un ticket se añade una revisión nueva, que se puede consultar desde el detalle del ticket.

Docker Compose conserva los datos en el volumen nombrado `ticketflow_data`. La aplicación local usa `instance/ticketflow.sqlite3`. SQLite es adecuado para una instancia pequeña o de un solo servidor; para varias instancias concurrentes o un despliegue de alta disponibilidad, conviene migrar a PostgreSQL y configurar almacenamiento y copias de seguridad administrados.

La aplicación todavía no incluye autenticación ni permisos por usuario.

## Licencia

Consulta el archivo [LICENSE](LICENSE) para conocer los términos de uso.
