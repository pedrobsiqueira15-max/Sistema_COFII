import os
import sys

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import create_app
from app.extensions import db
from app.models import User


def main():
    if len(sys.argv) < 4:
        print("Uso: python scripts/create_user.py email nome senha")
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    name = sys.argv[2].strip()
    password = sys.argv[3]

    app = create_app()
    with app.app_context():
        if User.query.filter_by(email=email).first():
            print("Usuario ja existe.")
            sys.exit(1)
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Usuario criado.")


if __name__ == "__main__":
    main()
