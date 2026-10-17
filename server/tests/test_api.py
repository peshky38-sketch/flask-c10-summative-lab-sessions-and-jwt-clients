import pytest
from app import create_app
from extensions import db
from models import User

@pytest.fixture()
def app(tmp_path):
    test_db = tmp_path / "test.sqlite"
    app = create_app({"TESTING": True,
                      "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db.as_posix()}",
                      "JWT_SECRET_KEY": "test-jwt-secret-for-local-tests-32",
                      "SECRET_KEY": "test-secret"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def register(client, username="alice", email="alice@example.com"):
    return client.post("/api/auth/register", json={
        "username": username, "email": email, "password": "Password123!"})

def headers(client, username="alice"):
    r = client.post("/api/auth/login", json={"username": username, "password": "Password123!"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json['access_token']}"}

def test_registration_hashes_password(client, app):
    r = register(client)
    assert r.status_code == 201 and "access_token" in r.json
    with app.app_context():
        user = User.query.filter_by(username="alice").first()
        assert user.password_hash != "Password123!"
        assert user.check_password("Password123!")

def test_private_route_requires_token(client):
    assert client.get("/api/notes").status_code == 401

def test_create_and_paginate_notes(client):
    register(client)
    h = headers(client)
    r = client.post("/api/notes", json={"title": "Study", "content": "Flask JWT"}, headers=h)
    assert r.status_code == 201
    listed = client.get("/api/notes?page=1&per_page=5", headers=h)
    assert listed.status_code == 200
    assert listed.json["pagination"]["total"] == 1

def test_user_cannot_access_another_users_note(client):
    register(client, "alice", "alice@example.com")
    alice = headers(client, "alice")
    r = client.post("/api/notes", json={"title": "Private", "content": "Secret"}, headers=alice)
    note_id = r.json["note"]["id"]
    register(client, "bob", "bob@example.com")
    bob = headers(client, "bob")
    assert client.get(f"/api/notes/{note_id}", headers=bob).status_code == 404
    assert client.patch(f"/api/notes/{note_id}", json={"title": "Stolen"}, headers=bob).status_code == 404
    assert client.delete(f"/api/notes/{note_id}", headers=bob).status_code == 404

def test_update_delete_and_logout(client):
    register(client)
    h = headers(client)
    r = client.post("/api/notes", json={"title": "Old", "content": "Text"}, headers=h)
    note_id = r.json["note"]["id"]
    assert client.patch(f"/api/notes/{note_id}", json={"title": "New"}, headers=h).status_code == 200
    assert client.delete(f"/api/notes/{note_id}", headers=h).status_code == 200
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/notes", headers=h).status_code == 401
