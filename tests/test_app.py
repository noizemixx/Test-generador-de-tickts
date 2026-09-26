import pytest

from app import app, initialize_database


@pytest.fixture
def client(tmp_path):
    original_path = app.config["DATABASE_PATH"]
    app.config.update(TESTING=True, DATABASE_PATH=str(tmp_path / "tickets.sqlite3"))
    initialize_database()
    with app.test_client() as test_client:
        yield test_client
    app.config["DATABASE_PATH"] = original_path


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
