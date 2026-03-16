import csv
import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import create_app
from app.extensions import db
from app.models import PortfolioFund, Segment


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
                fund_code = row.get("fund_code", "").strip().upper()
                segment_name = row.get("segment", "").strip().lower()
                as_of_date = parse_date(row.get("as_of_date", ""))
                weight = to_float(row.get("weight")) or 0.0
                if segment_name not in segments_by_name:
                    print(f"Segmento nao encontrado: {segment_name}. Pulei {fund_code}.")
                    continue
                segment_id = segments_by_name[segment_name].id

                existing = PortfolioFund.query.filter_by(
                    fund_code=fund_code, as_of_date=as_of_date
                ).first()
                if existing:
                    existing.weight = weight
                    existing.segment_id = segment_id
                else:
                    db.session.add(
                        PortfolioFund(
                            fund_code=fund_code,
                            segment_id=segment_id,
                            as_of_date=as_of_date,
                            weight=weight,
                        )
                    )
        db.session.commit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_portfolio.py caminho_do_csv")
        sys.exit(1)
    import_file(sys.argv[1])
