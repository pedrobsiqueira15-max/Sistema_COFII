import csv
import sys
from datetime import datetime

from app.main import create_app
from app.extensions import db
from app.models import FundMetric


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
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                fund_code = row.get("fund_code", "").strip().upper()
                as_of_date = parse_date(row.get("as_of_date", ""))
                data = dict(
                    dy_12m=to_float(row.get("dy_12m")),
                    volatility=to_float(row.get("volatility")),
                    leverage=to_float(row.get("leverage")),
                    beta=to_float(row.get("beta")),
                    p_vp=to_float(row.get("p_vp")),
                )
                existing = FundMetric.query.filter_by(
                    fund_code=fund_code, as_of_date=as_of_date
                ).first()
                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.session.add(
                        FundMetric(
                            fund_code=fund_code,
                            as_of_date=as_of_date,
                            **data,
                        )
                    )
        db.session.commit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_economatica.py caminho_do_csv")
        sys.exit(1)
    import_file(sys.argv[1])
