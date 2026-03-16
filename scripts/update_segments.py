from app.main import create_app
from app.extensions import db
from app.models import Segment


RENAMES = {
    "Logistica": "Logística",
    "Hibrido": "Híbrido",
    "Fundo de Fundos": "FOF",
}

EXTRA_SEGMENTS = [
    "Renda Urbana",
]


def main():
    app = create_app()
    with app.app_context():
        existing = {s.name: s for s in Segment.query.all()}

        for old_name, new_name in RENAMES.items():
            segment = existing.get(old_name)
            if segment:
                segment.name = new_name

        existing_names = {s.name for s in Segment.query.all()}
        for name in EXTRA_SEGMENTS:
            if name not in existing_names:
                db.session.add(Segment(name=name))

        db.session.commit()
        print("Segmentos atualizados.")


if __name__ == "__main__":
    main()
