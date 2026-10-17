from faker import Faker
from app import create_app
from extensions import db
from models import Note, TokenBlocklist, User

fake = Faker()
app = create_app()

with app.app_context():
    # WARNING: this resets sample app data in the configured database.
    TokenBlocklist.query.delete()
    Note.query.delete()
    User.query.delete()
    db.session.commit()
    user = User(username="demo", email="demo@example.com")
    user.set_password("Password123!")
    db.session.add(user)
    db.session.flush()
    for _ in range(12):
        db.session.add(Note(title=fake.sentence(nb_words=4).rstrip("."),
                            content=fake.paragraph(), user_id=user.id))
    db.session.commit()
    print("Seeded demo user: demo / Password123!")
