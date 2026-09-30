import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

db = SQLAlchemy()

PRIORITIES = {
    "baja": ("Baja", "priority-low"),
    "media": ("Media", "priority-medium"),
    "alta": ("Alta", "priority-high"),
    "critica": ("Crítica", "priority-critical"),
}
CATEGORIES = ("Soporte", "Acceso y cuentas", "Hardware", "Software", "Redes", "Otro")
TICKET_FIELDS = ("requester", "email", "category", "priority", "subject", "description")


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), nullable=False, unique=True)
    requester = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(320), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(40), nullable=False)
    updated_at = db.Column(db.String(40), nullable=False)
    versions = db.relationship(
        "TicketVersion",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketVersion.version",
    )


class TicketVersion(db.Model):
    __tablename__ = "ticket_versions"
    __table_args__ = (
        db.UniqueConstraint("ticket_id", "version", name="uq_ticket_version"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    version = db.Column(db.Integer, nullable=False)
    requester = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(320), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    changed_at = db.Column(db.String(40), nullable=False)
    ticket = db.relationship("Ticket", back_populates="versions")


def database_uri(app):
    configured_uri = os.environ.get("DATABASE_URL")
    if configured_uri:
        if configured_uri.startswith("postgres://"):
            return configured_uri.replace("postgres://", "postgresql+psycopg://", 1)
        if configured_uri.startswith("postgresql://"):
            return configured_uri.replace("postgresql://", "postgresql+psycopg://", 1)
        return configured_uri

    postgres_host = os.environ.get("POSTGRES_HOST")
    if postgres_host:
        password_file = os.environ.get("POSTGRES_PASSWORD_FILE")
        password = (
            Path(password_file).read_text(encoding="utf-8").strip()
            if password_file
            else os.environ.get("POSTGRES_PASSWORD", "")
        )
        return URL.create(
            "postgresql+psycopg",
            username=os.environ.get("POSTGRES_USER", "ticketflow"),
            password=password,
            host=postgres_host,
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ.get("POSTGRES_DB", "ticketflow"),
        )

    sqlite_path = os.environ.get(
        "TICKETFLOW_DB", os.path.join(app.instance_path, "ticketflow.sqlite3")
    )
    os.makedirs(os.path.dirname(sqlite_path) or ".", exist_ok=True)
    return URL.create("sqlite", database=os.path.abspath(sqlite_path))


def create_app(test_config=None):
    application = Flask(__name__)
    application.config.update(
        SQLALCHEMY_DATABASE_URI=database_uri(application),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    )
    if test_config:
        application.config.update(test_config)

    db.init_app(application)
    with application.app_context():
        if db.engine.dialect.name == "sqlite":
            event.listen(
                db.engine,
                "connect",
                lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
            )
            db.create_all()
        elif db.engine.dialect.name == "postgresql":
            with db.engine.begin() as connection:
                connection.execute(text("SELECT pg_advisory_xact_lock(73421901)"))
                db.metadata.create_all(bind=connection)
        else:
            db.create_all()

    register_routes(application)
    return application


def validate_ticket_form(form):
    values = {field: form.get(field, "").strip() for field in TICKET_FIELDS}
    if any(not values[field] for field in TICKET_FIELDS):
        raise ValueError("Completa todos los campos del ticket.")
    if values["category"] not in CATEGORIES:
        raise ValueError("Selecciona una categoría válida.")
    if values["priority"] not in PRIORITIES:
        raise ValueError("Selecciona una prioridad válida.")
    return values


def add_ticket_version(ticket, version, values, changed_at):
    ticket.versions.append(
        TicketVersion(
            version=version,
            **values,
            changed_at=changed_at,
        )
    )


def create_ticket(values):
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ticket = Ticket(
        number=f"PENDING-{uuid4().hex}",
        **values,
        created_at=created_at,
        updated_at=created_at,
    )
    db.session.add(ticket)
    db.session.flush()
    ticket.number = f"TCK-{datetime.now(timezone.utc):%Y%m%d}-{ticket.id:06d}"
    add_ticket_version(ticket, 1, values, created_at)
    db.session.commit()
    return ticket.id


def update_ticket(ticket_id, values):
    ticket = db.session.execute(
        select(Ticket).where(Ticket.id == ticket_id).with_for_update()
    ).scalar_one_or_none()
    if ticket is None:
        return False

    changed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    version = db.session.scalar(
        select(func.coalesce(func.max(TicketVersion.version), 0) + 1).where(
            TicketVersion.ticket_id == ticket_id
        )
    )
    for field, value in values.items():
        setattr(ticket, field, value)
    ticket.updated_at = changed_at
    add_ticket_version(ticket, version, values, changed_at)
    db.session.commit()
    return True


def ticket_to_dict(ticket, version_count=None):
    result = {
        field: getattr(ticket, field)
        for field in (
            "id",
            "number",
            *TICKET_FIELDS,
            "created_at",
            "updated_at",
        )
    }
    if version_count is not None:
        result["version_count"] = version_count
    return result


def get_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    return ticket_to_dict(ticket) if ticket else None


def list_tickets():
    records = db.session.execute(
        select(Ticket)
        .options(selectinload(Ticket.versions))
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
    ).scalars()
    return [ticket_to_dict(ticket, len(ticket.versions)) for ticket in records]


def list_ticket_versions(ticket_id):
    versions = db.session.execute(
        select(TicketVersion)
        .where(TicketVersion.ticket_id == ticket_id)
        .order_by(TicketVersion.version.desc())
    ).scalars()
    return [
        {
            "version": version.version,
            **{field: getattr(version, field) for field in TICKET_FIELDS},
            "changed_at": version.changed_at,
        }
        for version in versions
    ]


def ticket_view(ticket):
    if ticket is not None:
        ticket["priority_label"], ticket["priority_class"] = PRIORITIES.get(
            ticket["priority"], PRIORITIES["media"]
        )
    return ticket


def register_routes(application):
    @application.template_filter("local_time")
    def local_time(value):
        return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y %H:%M")

    @application.get("/health")
    def health():
        try:
            db.session.execute(select(1))
        except SQLAlchemyError:
            db.session.rollback()
            return {"status": "unavailable"}, 503
        return {"status": "ok"}, 200

    @application.route("/", methods=["GET", "POST"])
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

    @application.get("/tickets")
    def tickets():
        ticket_rows = [ticket_view(ticket) for ticket in list_tickets()]
        return render_template("tickets.html", tickets=ticket_rows)

    @application.get("/tickets/<int:ticket_id>")
    def ticket_detail(ticket_id):
        ticket = ticket_view(get_ticket(ticket_id))
        if ticket is None:
            abort(404)
        return render_template("ticket_detail.html", ticket=ticket)

    @application.route("/tickets/<int:ticket_id>/edit", methods=["GET", "POST"])
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

    @application.get("/tickets/<int:ticket_id>/history")
    def ticket_history(ticket_id):
        ticket = ticket_view(get_ticket(ticket_id))
        if ticket is None:
            abort(404)
        versions = [ticket_view(version) for version in list_ticket_versions(ticket_id)]
        return render_template("ticket_history.html", ticket=ticket, versions=versions)


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
