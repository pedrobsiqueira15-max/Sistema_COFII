"""
Processamento do datafeed Economatica (CSV).
Usado pelo script import_economatica_url e pela rota de upload do dashboard.
Deve ser chamado dentro do app context (request ou with app.app_context()).
"""
import csv
import re
from datetime import date, datetime
from typing import Optional

from app.extensions import db
from app.models import Fund, FundMetric, IFIXComposition


DATE_PATTERN = re.compile(r"\|(\d{1,2}[A-Za-z]{3}\d{2})\|")
MONTH_YEAR_PATTERN = re.compile(r"\|([A-Za-z]{3}\d{2})\|")

MONTH_MAP = {
    "JAN": "Jan", "FEV": "Feb", "FEB": "Feb", "MAR": "Mar",
    "ABR": "Apr", "APR": "Apr", "MAI": "May", "MAY": "May",
    "JUN": "Jun", "JUL": "Jul", "AGO": "Aug", "AUG": "Aug",
    "SET": "Sep", "SEP": "Sep", "OUT": "Oct", "OCT": "Oct",
    "NOV": "Nov", "DEZ": "Dec", "DEC": "Dec",
}


def parse_date_from_header(header: str) -> Optional[date]:
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


def to_float(value: Optional[str]):
    if value is None:
        return None
    value = str(value).strip()
    if value in {"", "-", "NA"}:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            value_br = value.replace(".", "").replace(",", ".")
            return float(value_br)
        except ValueError:
            return None


def import_datafeed_from_csv_text(csv_text: str) -> tuple[int, int]:
    """
    Processa o conteúdo CSV do datafeed Economatica e grava no banco
    (fund_metrics, ifix_composition, e atualiza/cria funds).
    Deve ser chamado dentro do app context.
    Retorna (num_fund_metrics, num_ifix).
    """
    reader = csv.DictReader(csv_text.splitlines())
    if not reader.fieldnames:
        raise ValueError("CSV sem cabecalho.")

    dy_header = next((h for h in reader.fieldnames if h.startswith("Div Yld")), "")
    vol_header = next((h for h in reader.fieldnames if h.startswith("Volatilidade")), "")
    beta_header = next((h for h in reader.fieldnames if h.startswith("Beta")), "")
    pvp_header = next((h for h in reader.fieldnames if h.startswith("P/VPA")), "")
    patrimonio_header = next((h for h in reader.fieldnames if h.startswith("Patrim Liq")), "")
    passivo_header = next((h for h in reader.fieldnames if h.startswith("PssvTt")), "")
    ifix_header = next(
        (h for h in reader.fieldnames if "Comp carteira" in h and "Ind Fdo Imob" in h), ""
    )
    codigo_header = next(
        (h for h in reader.fieldnames if "odigo" in h.lower() and len(h) <= 12), None
    )

    as_of = (
        parse_date_from_header(dy_header)
        or parse_date_from_header(vol_header)
        or date.today()
    )

    num_metrics = 0
    num_ifix = 0

    for row in reader:
        fund_code = (row.get(codigo_header) if codigo_header else "") or row.get("Codigo") or ""
        fund_code = str(fund_code).strip().upper()
        if not fund_code and row.get("Ativo"):
            ativo = str(row.get("Ativo", "")).strip()
            fund_code = (ativo.split("<")[0] if "<" in ativo else ativo).strip().upper()
        if not fund_code:
            continue

        fund_name = row.get("Nome", "").strip()
        if fund_name:
            fund = Fund.query.filter_by(fund_code=fund_code).first()
            if not fund:
                fund = Fund(fund_code=fund_code, name=fund_name)
                db.session.add(fund)
            elif fund.name != fund_name:
                fund.name = fund_name
                fund.updated_at = datetime.utcnow()

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
        num_metrics += 1

        if ifix_header:
            ifix_weight = to_float(row.get(ifix_header))
            if ifix_weight is not None and ifix_weight >= 0:
                existing_ifix = IFIXComposition.query.filter_by(
                    fund_code=fund_code, as_of_date=as_of
                ).first()
                if existing_ifix:
                    existing_ifix.weight = ifix_weight
                else:
                    db.session.add(
                        IFIXComposition(
                            fund_code=fund_code,
                            as_of_date=as_of,
                            weight=ifix_weight,
                        )
                    )
                num_ifix += 1

    db.session.commit()
    return num_metrics, num_ifix
