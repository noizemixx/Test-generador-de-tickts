# TicketFlow

Interfaz web para generar tickets de mesa de ayuda. Permite registrar solicitante, correo, categoría, prioridad y descripción; al enviar, genera un identificador único y una vista previa que se puede copiar al portapapeles.

## Ejecutar con Docker

```bash
docker compose up --build
```

Abre [http://localhost:5000](http://localhost:5000).

Para detener el servicio:

```bash
docker compose down
```

## Ejecutar localmente

Requiere Python 3.11 o superior:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

La aplicación escucha en `http://localhost:5000`. Los tickets se generan en memoria y no se persisten todavía en una base de datos.
