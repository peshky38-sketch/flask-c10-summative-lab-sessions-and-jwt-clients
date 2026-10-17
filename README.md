# Secure Notes API (Flask + JWT)

A personal Notes REST API with registration, login, bcrypt password hashing, JWT authentication, user-owned records, pagination, logout token revocation, migrations, seed data, and tests.

## Requirements
Python 3.8.13+ and Pipenv. The provided Pipfile targets Python 3.12. If you use another installed Python version, update `python_version` in `Pipfile` before installing.

## Install and database setup
Run from the project root:

```bash
pipenv install --dev
cd server
pipenv run flask --app app db init
pipenv run flask --app app db migrate -m "Create users and notes tables"
pipenv run flask --app app db upgrade
pipenv run python seed.py
```

Only run `db init` the first time. Commit the generated `server/migrations/` directory. The seed script resets the app's sample data, creates demo / Password123!, and adds twelve fake notes. Do not run it if you need to preserve data.

## Run
From `server/`:

```bash
pipenv run flask --app app run --port 5555
```

Health endpoint: `GET http://127.0.0.1:5555/api/health`

Set strong `SECRET_KEY` and `JWT_SECRET_KEY` environment variables before deployment. Default values are only for local development.

## Authentication endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Register using `username`, `email`, `password`; returns `access_token` |
| POST | `/api/auth/login` | Login using `username` or `email` and `password`; returns `access_token` |
| GET | `/api/auth/me` | Get current user's profile (Bearer token required) |
| POST | `/api/auth/logout` | Revoke current access token (Bearer token required) |

Send protected requests with header `Authorization: Bearer YOUR_ACCESS_TOKEN`.

## Notes endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/notes?page=1&per_page=10` | Paginated list of the authenticated user's notes |
| POST | `/api/notes` | Create note with `title` and `content` |
| GET | `/api/notes/<id>` | Read one owned note |
| PATCH | `/api/notes/<id>` | Update `title` and/or `content` |
| DELETE | `/api/notes/<id>` | Delete an owned note |

The backend derives note ownership from the JWT identity, not from user-supplied `user_id`. Requests for another user's note return 404. `per_page` is capped at 100.

Example registration JSON:
```json
{"username":"alice","email":"alice@example.com","password":"Password123!"}
```

Example note JSON:
```json
{"title":"Study plan","content":"Review Flask authentication."}
```

## Tests
Run from the project root:
```bash
python -m pipenv run pytest -v server/tests
```
Or run from the `server/` directory:
```bash
python -m pipenv run pytest -v
```
Tests use a temporary database.

## Git workflow
```bash
git switch -c notes-jwt-api
git add .
git commit -m "Build secure JWT Notes API"
git push -u origin notes-jwt-api
```
Then open a Pull Request from `notes-jwt-api` into `main` and merge after reviewing.

## Security
Tokens expire after two hours and logout revokes a token using its JWT ID. Use HTTPS and restrict CORS origins to your actual frontend domain in deployment. Never commit secrets.
