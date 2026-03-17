import csv
import os
import re
import sys
from datetime import date, datetime
from urllib.request import urlopen

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import create_app
from app.extensions import db
from app.models import Fund, FundMetric


DATE_PATTERN = re.compile(r"\|(\d{1,2}[A-Za-z]{3}\d{2})\|")
MONTH_YEAR_PATTERN = re.compile(r"\|([A-Za-z]{3}\d{2})\|")


MONTH_MAP = {
    "JAN": "Jan",
    "FEV": "Feb",
    "FEB": "Feb",
    "MAR": "Mar",
    "ABR": "Apr",
    "APR": "Apr",
    "MAI": "May",
    "MAY": "May",
    "JUN": "Jun",
    "JUL": "Jul",
    "AGO": "Aug",
    "AUG": "Aug",
    "SET": "Sep",
    "SEP": "Sep",
    "OUT": "Oct",
    "OCT": "Oct",
    "NOV": "Nov",
    "DEZ": "Dec",
    "DEC": "Dec",
}


def parse_date_from_header(header: str) -> date | None:
    if not header:
        return None
    match = DATE_PATTERN.search(header)
    if match:
        raw = match.group(1)
        normalized = raw[:2] + MONTH_MAP.get(raw[2:5].upper(), raw[2:5]) + raw[5:]
        return datetime.strptime(normalized, "%d%b%y").date()
    match = MONTH_YEAR_PATTERN.search(header)
    if match:
        raw = match.group(1)
        normalized = "01" + MONTH_MAP.get(raw[:3].upper(), raw[:3]) + raw[3:]
        return datetime.strptime(normalized, "%d%b%y").date()
    return None


def to_float(value: str | None):
    if value is None:
        return None
    value = value.strip().replace(".", "").replace(",", ".")
    if value in {"", "-", "NA"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def download_csv(url: str) -> str:
    with urlopen(url) as response:
        return response.read().decode("utf-8-sig")


def import_from_url(url: str):
    csv_text = download_csv(url)
    reader = csv.DictReader(csv_text.splitlines())
    if not reader.fieldnames:
        raise ValueError("CSV sem cabecalho.")

    dy_header = next((h for h in reader.fieldnames if h.startswith("Div Yld")), "")
    vol_header = next((h for h in reader.fieldnames if h.startswith("Volatilidade")), "")
    beta_header = next((h for h in reader.fieldnames if h.startswith("Beta")), "")
    pvp_header = next((h for h in reader.fieldnames if h.startswith("P/VPA")), "")
    patrimonio_header = next((h for h in reader.fieldnames if h.startswith("Patrim Liq")), "")
    passivo_header = next((h for h in reader.fieldnames if h.startswith("PssvTt")), "")

    as_of = parse_date_from_header(dy_header) or parse_date_from_header(vol_header) or date.today()

    app = create_app()
    with app.app_context():
        for row in reader:
            fund_code = row.get("C�digo") or row.get("Código") or row.get("Codigo") or ""
            fund_code = fund_code.strip().upper()
            if not fund_code:
                continue

            dy_12m = to_float(row.get(dy_header))
            volatility = to_float(row.get(vol_header))
            beta = to_float(row.get(beta_header))
            p_vp = to_float(row.get(pvp_header))

            patrimonio = to_float(row.get(patrimonio_header))
            passivo = to_float(row.get(passivo_header))
            leverage = None
            if patrimonio and passivo and patrimonio != 0:
                leverage = passivo / patrimonio

            existing = FundMetric.query.filter_by(
                fund_code=fund_code, as_of_date=as_of
            ).first()
            if existing:
                existing.dy_12m = dy_12m
                existing.volatility = volatility
                existing.leverage = leverage
                existing.beta = beta
                existing.p_vp = p_vp
            else:
                db.session.add(
                    FundMetric(
                        fund_code=fund_code,
                        as_of_date=as_of,
                        dy_12m=dy_12m,
                        volatility=volatility,
                        leverage=leverage,
                        beta=beta,
                        p_vp=p_vp,
                    )
                )
        db.session.commit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_economatica_url.py <url>")
        sys.exit(1)
    import_from_url(sys.argv[1])
