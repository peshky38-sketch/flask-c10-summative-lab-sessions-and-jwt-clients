import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from extensions import bcrypt, db, jwt, migrate
from models import Note, TokenBlocklist, User


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db_path = Path(app.instance_path) / "notes.sqlite"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret"),
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "dev-only-change-this-jwt-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{db_path.as_posix()}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=2),
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @jwt.token_in_blocklist_loader
    def token_revoked(jwt_header, jwt_payload):
        return db.session.query(
            db.session.query(TokenBlocklist.id).filter_by(jti=jwt_payload["jti"]).exists()
        ).scalar()

    @app.get("/")
    def index():
        return jsonify({"message": "Notes API is running", "health": "/api/health"}), 200

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object."}), 400
        username, email, password = data.get("username"), data.get("email"), data.get("password")
        if not all(isinstance(v, str) and v.strip() for v in (username, email, password)):
            return jsonify({"error": "username, email, and password are required."}), 400
        username, email = username.strip(), email.strip().lower()
        if len(username) > 80 or len(email) > 255 or "@" not in email:
            return jsonify({"error": "Please provide a valid username and email."}), 400
        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters."}), 400
        if User.query.filter(or_(User.username == username, User.email == email)).first():
            return jsonify({"error": "Username or email already exists."}), 409
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Username or email already exists."}), 409
        token = create_access_token(identity=str(user.id))
        return jsonify({"message": "Registration successful.", "access_token": token,
                        "user": user.to_dict()}), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object."}), 400
        login_value, password = data.get("username") or data.get("email"), data.get("password")
        if not isinstance(login_value, str) or not login_value.strip() or not isinstance(password, str):
            return jsonify({"error": "username/email and password are required."}), 400
        login_value = login_value.strip()
        user = User.query.filter(or_(User.username == login_value,
                                     User.email == login_value.lower())).first()
        if user is None or not user.check_password(password):
            return jsonify({"error": "Invalid username/email or password."}), 401
        token = create_access_token(identity=str(user.id))
        return jsonify({"message": "Login successful.", "access_token": token,
                        "user": user.to_dict()}), 200

    @app.get("/api/auth/me")
    @jwt_required()
    def me():
        user = db.session.get(User, int(get_jwt_identity()))
        if user is None:
            return jsonify({"error": "User not found."}), 404
        return jsonify({"user": user.to_dict()}), 200

    @app.post("/api/auth/logout")
    @jwt_required()
    def logout():
        db.session.add(TokenBlocklist(jti=get_jwt()["jti"]))
        db.session.commit()
        return jsonify({"message": "Successfully logged out."}), 200

    @app.get("/api/notes")
    @jwt_required()
    def list_notes():
        try:
            page = max(int(request.args.get("page", 1)), 1)
            per_page = min(max(int(request.args.get("per_page", 10)), 1), 100)
        except ValueError:
            return jsonify({"error": "page and per_page must be integers."}), 400
        result = Note.query.filter_by(user_id=int(get_jwt_identity())).order_by(
            Note.created_at.desc(), Note.id.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({"notes": [n.to_dict() for n in result.items],
                        "pagination": {"page": result.page, "per_page": result.per_page,
                                       "total": result.total, "pages": result.pages,
                                       "has_next": result.has_next, "has_prev": result.has_prev}}), 200

    @app.post("/api/notes")
    @jwt_required()
    def create_note():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object."}), 400
        title, content = data.get("title"), data.get("content")
        if not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title is required and cannot be blank."}), 400
        if len(title.strip()) > 160:
            return jsonify({"error": "title must be 160 characters or fewer."}), 400
        if not isinstance(content, str) or not content.strip():
            return jsonify({"error": "content is required and cannot be blank."}), 400
        note = Note(title=title.strip(), content=content.strip(), user_id=int(get_jwt_identity()))
        db.session.add(note)
        db.session.commit()
        return jsonify({"message": "Note created.", "note": note.to_dict()}), 201

    @app.get("/api/notes/<int:note_id>")
    @jwt_required()
    def get_note(note_id):
        note = Note.query.filter_by(id=note_id, user_id=int(get_jwt_identity())).first()
        if note is None:
            return jsonify({"error": "Note not found."}), 404
        return jsonify({"note": note.to_dict()}), 200

    @app.patch("/api/notes/<int:note_id>")
    @jwt_required()
    def update_note(note_id):
        note = Note.query.filter_by(id=note_id, user_id=int(get_jwt_identity())).first()
        if note is None:
            return jsonify({"error": "Note not found."}), 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data or not set(data).intersection({"title", "content"}):
            return jsonify({"error": "Provide a JSON object with title and/or content."}), 400
        if "title" in data:
            if not isinstance(data["title"], str) or not data["title"].strip() or len(data["title"].strip()) > 160:
                return jsonify({"error": "title must be nonblank and 160 characters or fewer."}), 400
            note.title = data["title"].strip()
        if "content" in data:
            if not isinstance(data["content"], str) or not data["content"].strip():
                return jsonify({"error": "content cannot be blank."}), 400
            note.content = data["content"].strip()
        db.session.commit()
        return jsonify({"message": "Note updated.", "note": note.to_dict()}), 200

    @app.delete("/api/notes/<int:note_id>")
    @jwt_required()
    def delete_note(note_id):
        note = Note.query.filter_by(id=note_id, user_id=int(get_jwt_identity())).first()
        if note is None:
            return jsonify({"error": "Note not found."}), 404
        db.session.delete(note)
        db.session.commit()
        return jsonify({"message": "Note deleted."}), 200

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Route not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed for this route."}), 405

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=5555, debug=True)
