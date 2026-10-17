try:
    from flask_bcrypt import Bcrypt  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class Bcrypt:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "flask_bcrypt is not installed. Install it with 'pip install flask-bcrypt'."
            )

try:
    from flask_jwt_extended import JWTManager  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class JWTManager:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "flask_jwt_extended is not installed. Install it with 'pip install flask-jwt-extended'."
            )
try:
    from flask_migrate import Migrate  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class Migrate:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "flask_migrate is not installed. Install it with 'pip install Flask-Migrate'."
            )

try:
    from flask_sqlalchemy import SQLAlchemy  # type: ignore[import-not-found]
except ModuleNotFoundError:
    class SQLAlchemy:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "flask_sqlalchemy is not installed. Install it with 'pip install Flask-SQLAlchemy'."
            )

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
