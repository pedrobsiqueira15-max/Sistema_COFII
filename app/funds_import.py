"""
Importação de FIIs a partir do Excel "Dados Cadastrais - FIIs".
Vincular código do FII ao segmento (setor) para o IFIX por segmento fechar corretamente.
Deve ser chamado dentro do app context.
"""
from datetime import datetime
from io import BytesIO
from typing import Optional

import pandas as pd

from app.extensions import db
from app.models import Fund, Segment


SETOR_TO_SEGMENT = {
    "CRI": "CRI",
    "Lajes Corporativas": "Lajes Corporativas",
    "Shoppings": "Shoppings",
    "Renda Urbana": "Renda Urbana",
    "Híbrido": "Híbrido",
    "Residencial": "Residencial",
    "Logística": "Logística",
    "Fundo de Fundos": "FOF",
    "FOF": "FOF",
    "Outros": "Outros",
}


def normalize_segment_name(setor: str) -> Optional[str]:
    if not setor or (isinstance(setor, float) and pd.isna(setor)):
        return None
    setor = str(setor).strip()
    if setor in SETOR_TO_SEGMENT:
        return SETOR_TO_SEGMENT[setor]
    for key, value in SETOR_TO_SEGMENT.items():
        if key.lower() == setor.lower():
            return value
    return None


def import_funds_from_excel_bytes(excel_bytes: bytes) -> tuple[int, int, list[str]]:
    """
    Processa o Excel de Dados Cadastrais (código, nome, setor) e atualiza a tabela funds.
    Deve ser chamado dentro do app context.
    Retorna (criados, atualizados, lista_de_erros).
    """
    segments_by_name = {s.name: s.id for s in Segment.query.all()}
    df = pd.read_excel(BytesIO(excel_bytes))
    created = 0
    updated = 0
    errors = []

    for idx, row in df.iterrows():
        fund_code = None
        for col in ["codigo_negociacao", "ticker", "codigo"]:
            if col in df.columns and pd.notna(row.get(col)):
                fund_code = str(row[col]).strip().upper()
                break
        if not fund_code:
            continue

        name = None
        for col in ["nome_pregao", "nome_capitania", "razao_social", "nome"]:
            if col in df.columns and pd.notna(row.get(col)):
                name = str(row[col]).strip()
                break
        if not name:
            errors.append(f"FII {fund_code} sem nome")
            continue

        segment_name = None
        if "setor" in df.columns and pd.notna(row.get("setor")):
            segment_name = normalize_segment_name(str(row["setor"]).strip())
        segment_id = segments_by_name.get(segment_name) if segment_name else None
        if segment_name and not segment_id:
            errors.append(f"Segmento '{segment_name}' não encontrado para {fund_code}")

        fund = Fund.query.filter_by(fund_code=fund_code).first()
        if fund:
            fund.name = name
            if segment_id is not None:
                fund.segment_id = segment_id
            fund.updated_at = datetime.utcnow()
            updated += 1
        else:
            db.session.add(
                Fund(
                    fund_code=fund_code,
                    name=name,
                    segment_id=segment_id,
                )
            )
            created += 1

    db.session.commit()
    return created, updated, errors
