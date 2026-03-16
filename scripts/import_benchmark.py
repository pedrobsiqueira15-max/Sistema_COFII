import csv
import sys
from datetime import datetime

from app.main import create_app
from app.extensions import db
from app.models import BenchmarkWeight, Segment


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def to_float(value: str | None):
    if value is None:
        return None
    value = value.strip().replace(",", ".")
    if value == "":
        return None
    return float(value)


def import_file(path: str):
    app = create_app()
    with app.app_context():
        segments_by_name = {s.name.lower(): s for s in Segment.query.all()}
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                segment_name = row.get("segment", "").strip().lower()
                as_of_date = parse_date(row.get("as_of_date", ""))
                weight = to_float(row.get("weight")) or 0.0
                if segment_name not in segments_by_name:
                    print(f"Segmento nao encontrado: {segment_name}. Pulei.")
                    continue
                segment_id = segments_by_name[segment_name].id

                existing = BenchmarkWeight.query.filter_by(
                    segment_id=segment_id, as_of_date=as_of_date
                ).first()
                if existing:
                    existing.weight = weight
                else:
                    db.session.add(
                        BenchmarkWeight(
                            segment_id=segment_id,
                            as_of_date=as_of_date,
                            weight=weight,
                        )
                    )
        db.session.commit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_benchmark.py caminho_do_csv")
        sys.exit(1)
    import_file(sys.argv[1])
