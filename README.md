# TicketFlow

Aplicación web para generar y administrar tickets de mesa de ayuda. Guarda tickets e historial de versiones en SQLite para uso local y PostgreSQL para despliegues productivos con Docker Swarm.

## Funcionalidades

- Formulario responsive en español.
- Categorías y prioridades configurables.
- Identificador automático para cada ticket.
- Edición con una nueva versión por guardado, sin sobrescribir el historial.
- Vistas para listar tickets, consultar detalles y revisar versiones anteriores.
- Persistencia seleccionable entre SQLite y PostgreSQL.
- Health check HTTP en `/health`.

## Requisitos

- Docker Engine con Docker Swarm habilitado para los stacks.
- Un nodo manager; para producción, un registry accesible por todos los nodos.
- Python 3.11 o superior y `pip` para ejecución local.

## Desarrollo local con Docker Compose

Construye y levanta la aplicación con SQLite:

```bash
docker compose up --build
```

Abre [http://localhost:5000](http://localhost:5000). Los datos se guardan en el volumen `ticketflow_local_data`.

Para detener y eliminar los contenedores, conservando el volumen:

```bash
docker compose down
```

Para borrar también todos los tickets locales:

```bash
docker compose down -v
```

Para levantarlo en segundo plano y consultar los logs:

```bash
docker compose up --build -d
docker compose logs -f
```

## Docker Swarm: testing local con SQLite

Este stack es para pruebas en un Swarm de un solo nodo. SQLite está configurado con una sola réplica, fijada al nodo que contiene su volumen local:

```bash
docker swarm init
docker node update --label-add ticketflow.sqlite=true "$(docker node ls -q | head -n 1)"
docker build -t ticketflow:local .
docker stack deploy -c docker-stack.test.yml ticketflow-test
```

Visita [http://localhost:5000](http://localhost:5000) y consulta el estado/logs:

```bash
docker stack services ticketflow-test
docker service logs -f ticketflow-test_ticketflow
```

Detener y eliminar el stack **sin perder los datos**:

```bash
docker stack rm ticketflow-test
```

Volver a desplegarlo conserva el volumen `ticketflow_test_data`. Para eliminar definitivamente los tickets:

```bash
docker volume rm ticketflow_test_data
```

No escales este servicio ni muevas el volumen local a otro nodo. SQLite no está configurado para uso concurrente entre réplicas.

## Docker Swarm: producción con PostgreSQL

El stack productivo despliega dos réplicas web que comparten PostgreSQL. La base de datos usa un volumen local y se fija a un nodo concreto; no es una configuración PostgreSQL de alta disponibilidad.

PostgreSQL comienza con su propia base vacía; los tickets existentes en SQLite no se copian automáticamente.

### Preparar Swarm y secreto de base de datos

Inicializa Swarm si todavía no está activo y etiqueta el nodo donde se alojará PostgreSQL:

```bash
docker swarm init
docker node update --label-add ticketflow.postgres=true <ID_DEL_NODO>
```

Crea el secreto de contraseña de manera interactiva para que no quede escrito en el historial del shell:

```bash
read -rsp "Contraseña de PostgreSQL: " TICKETFLOW_DB_PASSWORD
printf '%s' "$TICKETFLOW_DB_PASSWORD" | docker secret create ticketflow_db_password -
unset TICKETFLOW_DB_PASSWORD
```

### Publicar la imagen

Todos los nodos deben poder descargar la imagen desde el registry. Inicia sesión y publica una etiqueta versionada:

```bash
docker login ghcr.io
export TICKETFLOW_IMAGE=ghcr.io/USUARIO/test-generador-de-tickts:1.0.0
docker build -t "$TICKETFLOW_IMAGE" .
docker push "$TICKETFLOW_IMAGE"
```

### Desplegar y administrar el stack

```bash
docker stack deploy --with-registry-auth \
  -c docker-stack.production.yml ticketflow
```

La web queda publicada en el puerto `5000` de los nodos Swarm. Revisa servicios y logs:

```bash
docker stack services ticketflow
docker service logs -f ticketflow_web
docker service logs -f ticketflow_db
```

Escala las réplicas web cuando lo necesites:

```bash
docker service scale ticketflow_web=3
```

Detén y elimina los servicios conservando la base de datos:

```bash
docker stack rm ticketflow
```

El volumen `ticketflow_postgres_data` permanece después de quitar el stack. **No lo elimines si necesitas conservar los tickets.** Su borrado es destructivo:

```bash
docker volume rm ticketflow_postgres_data
```

Antes de producción, configura copias de seguridad PostgreSQL, almacenamiento duradero, firewall/TLS y autenticación. La aplicación aún no incluye autenticación de usuarios.

## Ejecutar localmente con Python

Crear y activar un entorno virtual, instalar dependencias e iniciar con SQLite:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abre [http://localhost:5000](http://localhost:5000). La base local se crea en `instance/ticketflow.sqlite3`; puedes configurar otra ruta con `TICKETFLOW_DB`. Para detener el servidor, presiona `Ctrl + C`. Salir del entorno virtual es opcional:

```bash
deactivate
```

## Configuración de base de datos

La aplicación selecciona el backend con estas variables:

- SQLite local: `TICKETFLOW_DB` (si no se configura, `instance/ticketflow.sqlite3`).
- PostgreSQL con URL: `DATABASE_URL`.
- PostgreSQL por variables: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` o `POSTGRES_PASSWORD_FILE`.

El stack de producción monta el secreto en `/run/secrets/ticketflow_db_password`. No guardes contraseñas en el repositorio.

## Ejecutar las pruebas

```bash
python -m pip install pytest
python -m pytest
```

Las pruebas cubren la creación, edición, historial, validación y tickets inexistentes usando SQLite temporal.

## Control de versiones con Git

Clonar el repositorio:

```bash
git clone https://github.com/noizemixx/Test-generador-de-tickts.git
cd Test-generador-de-tickts
```

Crear una rama y guardar los cambios:

```bash
git switch -c feature/nombre-del-cambio
git status
git add README.md app.py
git commit -m "Describe el cambio"
git push -u origin feature/nombre-del-cambio
```

Abre un Pull Request de esa rama hacia `main`. Para sincronizar cambios nuevos de `main`:

```bash
git fetch origin
git merge origin/main
```

La base de datos y los datos persistidos no se suben a Git.

## Estructura del proyecto

```text
.
├── app.py                     # Rutas Flask, SQLAlchemy y configuración de DB
├── templates/                 # Formulario, tickets e historial
├── static/style.css           # Estilos responsive
├── docker-compose.yml         # Desarrollo local con SQLite
├── docker-stack.test.yml      # Swarm de testing con SQLite
├── docker-stack.production.yml # Swarm de producción con PostgreSQL
├── Dockerfile
└── requirements.txt
```

## Licencia

Consulta el archivo [LICENSE](LICENSE) para conocer los términos de uso.
