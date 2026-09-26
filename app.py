import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["DATABASE_PATH"] = os.environ.get(
    "TICKETFLOW_DB", os.path.join(app.instance_path, "ticketflow.sqlite3")
)

PRIORITIES = {
    "baja": ("Baja", "priority-low"),
    "media": ("Media", "priority-medium"),
    "alta": ("Alta", "priority-high"),
    "critica": ("Crítica", "priority-critical"),
}
CATEGORIES = ("Soporte", "Acceso y cuentas", "Hardware", "Software", "Redes", "Otro")
TICKET_FIELDS = ("requester", "email", "category", "priority", "subject", "description")


def connect_database():
    connection = sqlite3.connect(app.config["DATABASE_PATH"], timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]) or ".", exist_ok=True)
    with closing(connect_database()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL UNIQUE,
                requester TEXT NOT NULL,
                email TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ticket_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                version INTEGER NOT NULL,
                requester TEXT NOT NULL,
                email TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                UNIQUE(ticket_id, version)
            );
            """
        )


def validate_ticket_form(form):
    values = {field: form.get(field, "").strip() for field in TICKET_FIELDS}
    missing_fields = [field for field in TICKET_FIELDS if not values[field]]
    if missing_fields:
        raise ValueError("Completa todos los campos del ticket.")
    if values["category"] not in CATEGORIES:
        raise ValueError("Selecciona una categoría válida.")
    if values["priority"] not in PRIORITIES:
        raise ValueError("Selecciona una prioridad válida.")
    return values


def add_ticket_version(connection, ticket_id, version, values, changed_at):
    columns = ", ".join(TICKET_FIELDS)
    placeholders = ", ".join("?" for _ in TICKET_FIELDS)
    connection.execute(
        f"INSERT INTO ticket_versions "
        f"(ticket_id, version, {columns}, changed_at) "
        f"VALUES (?, ?, {placeholders}, ?)",
        (ticket_id, version, *(values[field] for field in TICKET_FIELDS), changed_at),
    )


def create_ticket(values):
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(connect_database()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO tickets
                    (number, requester, email, category, priority, subject,
                     description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("", *(values[field] for field in TICKET_FIELDS), created_at, created_at),
            )
            ticket_id = cursor.lastrowid
            number = f"TCK-{datetime.now(timezone.utc):%Y%m%d}-{ticket_id:06d}"
            connection.execute(
                "UPDATE tickets SET number = ? WHERE id = ?", (number, ticket_id)
            )
            add_ticket_version(connection, ticket_id, 1, values, created_at)
    return ticket_id


def update_ticket(ticket_id, values):
    changed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(connect_database()) as connection:
        with connection:
            assignments = ", ".join(f"{field} = ?" for field in TICKET_FIELDS)
            cursor = connection.execute(
                f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?",
                (*(values[field] for field in TICKET_FIELDS), changed_at, ticket_id),
            )
            if cursor.rowcount == 0:
                return False
            version = connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM ticket_versions "
                "WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()[0]
            add_ticket_version(connection, ticket_id, version, values, changed_at)
    return True


def get_ticket(ticket_id):
    with closing(connect_database()) as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    return dict(row) if row else None


def list_tickets():
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """
            SELECT tickets.*,
                   (SELECT MAX(version) FROM ticket_versions
                    WHERE ticket_id = tickets.id) AS version_count
            FROM tickets
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_ticket_versions(ticket_id):
    with closing(connect_database()) as connection:
        rows = connection.execute(
            """
            SELECT * FROM ticket_versions
            WHERE ticket_id = ?
            ORDER BY version DESC
            """,
            (ticket_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def ticket_view(ticket):
    if ticket is not None:
        ticket["priority_label"], ticket["priority_class"] = PRIORITIES.get(
            ticket["priority"], PRIORITIES["media"]
        )
    return ticket


@app.template_filter("local_time")
def local_time(value):
    return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y %H:%M")


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        try:
            values = validate_ticket_form(request.form)
        except ValueError as exc:
            error = str(exc)
        else:
            ticket_id = create_ticket(values)
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    return render_template("index.html", error=error, categories=CATEGORIES)


@app.get("/tickets")
def tickets():
    ticket_rows = [ticket_view(ticket) for ticket in list_tickets()]
    return render_template("tickets.html", tickets=ticket_rows)


@app.route("/tickets/<int:ticket_id>")
def ticket_detail(ticket_id):
    ticket = ticket_view(get_ticket(ticket_id))
    if ticket is None:
        abort(404)
    return render_template("ticket_detail.html", ticket=ticket)


@app.route("/tickets/<int:ticket_id>/edit", methods=["GET", "POST"])
def edit_ticket(ticket_id):
    ticket = get_ticket(ticket_id)
    if ticket is None:
        abort(404)
    error = None
    if request.method == "POST":
        try:
            values = validate_ticket_form(request.form)
        except ValueError as exc:
            error = str(exc)
        else:
            update_ticket(ticket_id, values)
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    return render_template(
        "ticket_form.html",
        ticket=ticket_view(ticket),
        error=error,
        categories=CATEGORIES,
    ), 400 if error else 200


@app.get("/tickets/<int:ticket_id>/history")
def ticket_history(ticket_id):
    ticket = ticket_view(get_ticket(ticket_id))
    if ticket is None:
        abort(404)
    versions = [ticket_view(version) for version in list_ticket_versions(ticket_id)]
    return render_template(
        "ticket_history.html", ticket=ticket, versions=versions
    )


initialize_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
