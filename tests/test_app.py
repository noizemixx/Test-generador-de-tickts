import sqlite3

import pytest
from flask import Flask

from app import create_app, database_uri, db


@pytest.fixture
def client(tmp_path):
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'tickets.sqlite3'}",
        }
    )
    with test_app.app_context():
        db.drop_all()
        db.create_all()
    with test_app.test_client() as test_client:
        yield test_client
    with test_app.app_context():
        db.drop_all()


def ticket_form(**overrides):
    values = {
        "requester": "Ana García",
        "email": "ana@example.com",
        "category": "Soporte",
        "priority": "media",
        "subject": "No puedo iniciar sesión",
        "description": "La cuenta está bloqueada.",
    }
    values.update(overrides)
    return values


def test_create_ticket_persists_and_shows_version_one(client):
    response = client.post("/", data=ticket_form())

    assert response.status_code == 302
    detail = client.get(response.headers["Location"])
    assert detail.status_code == 200
    assert b"TCK-" in detail.data
    assert b"No puedo iniciar sesi\xc3\xb3n" in detail.data

    tickets = client.get("/tickets")
    assert b"Versiones" in tickets.data
    assert b">1</td>" in tickets.data


def test_edit_ticket_keeps_previous_version(client):
    created = client.post("/", data=ticket_form())
    ticket_url = created.headers["Location"]
    edit_url = f"{ticket_url}/edit"

    edit_page = client.get(edit_url)
    assert edit_page.status_code == 200
    updated = client.post(
        edit_url,
        data=ticket_form(subject="Acceso restablecido", priority="alta"),
    )

    assert updated.status_code == 302
    detail = client.get(ticket_url)
    assert b"Acceso restablecido" in detail.data
    assert b"Alta" in detail.data

    history = client.get(f"{ticket_url}/history")
    assert b"Versi\xc3\xb3n 2" in history.data
    assert b"Versi\xc3\xb3n 1" in history.data
    assert b"No puedo iniciar sesi\xc3\xb3n" in history.data
    assert b"Acceso restablecido" in history.data


def test_invalid_ticket_form_is_rejected(client):
    response = client.post("/", data=ticket_form(priority="urgente"))

    assert response.status_code == 200
    assert b"Selecciona una prioridad v\xc3\xa1lida" in response.data
    assert client.get("/tickets").data.count(b"TCK-") == 0


def test_missing_ticket_returns_not_found(client):
    assert client.get("/tickets/999/history").status_code == 404


def test_health_check_reports_database_connection(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_postgres_configuration_reads_password_from_secret_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "postgres-password"
    secret_file.write_text("secret with spaces", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "database")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret_file))
    monkeypatch.setenv("POSTGRES_USER", "ticketflow")
    monkeypatch.setenv("POSTGRES_DB", "tickets")

    uri = database_uri(Flask(__name__))

    assert uri.drivername == "postgresql+psycopg"
    assert uri.host == "database"
    assert uri.database == "tickets"
    assert uri.password == "secret with spaces"


def test_existing_sqlite_schema_remains_usable(tmp_path):
    database_path = tmp_path / "existing.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE tickets (
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
            CREATE TABLE ticket_versions (
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
            INSERT INTO tickets VALUES
                (1, 'TCK-20260926-000001', 'Ana', 'ana@example.com', 'Soporte',
                 'media', 'Ticket anterior', 'Persistido', '2026-09-26T10:00:00+00:00',
                 '2026-09-26T10:00:00+00:00');
            INSERT INTO ticket_versions VALUES
                (1, 1, 1, 'Ana', 'ana@example.com', 'Soporte', 'media',
                 'Ticket anterior', 'Persistido', '2026-09-26T10:00:00+00:00');
            """
        )

    test_app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"}
    )
    response = test_app.test_client().get("/tickets")

    assert response.status_code == 200
    assert b"TCK-20260926-000001" in response.data
    assert b"Ticket anterior" in response.data
    with test_app.app_context():
        db.engine.dispose()
