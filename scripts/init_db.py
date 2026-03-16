import os

from app.main import create_app
from app.extensions import db
from app.models import Segment, User


DEFAULT_SEGMENTS = [
    "Logistica",
    "Lajes Corporativas",
    "Shoppings",
    "CRI",
    "Residencial",
    "Hibrido",
    "Fundo de Fundos",
    "Outros",
]


def seed_segments():
    existing = {s.name for s in Segment.query.all()}
    for name in DEFAULT_SEGMENTS:
        if name not in existing:
            db.session.add(Segment(name=name))
    db.session.commit()


def seed_admin_user():
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    name = os.environ.get("ADMIN_NAME", "Admin COFII")
    if not email or not password:
        print("ADMIN_EMAIL e ADMIN_PASSWORD nao definidos. Usuario admin nao criado.")
        return
    if User.query.filter_by(email=email).first():
        print("Usuario admin ja existe.")
        return
    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print("Usuario admin criado.")


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_segments()
        seed_admin_user()


if __name__ == "__main__":
    main()
