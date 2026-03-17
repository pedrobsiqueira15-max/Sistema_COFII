import os
import sys
from datetime import datetime
from typing import Optional

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import pandas as pd
except ImportError:
    print("ERRO: pandas e openpyxl sao necessarios. Instale com: pip install pandas openpyxl")
    sys.exit(1)

from app.main import create_app
from app.extensions import db
from app.models import Fund, Segment


# Mapeamento de setores do Excel para segmentos do sistema
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
    # Adicionar outros mapeamentos conforme necessário
}


def normalize_segment_name(setor: str) -> Optional[str]:
    """Normaliza o nome do setor para o segmento do sistema"""
    if not setor or pd.isna(setor):
        return None
    setor = str(setor).strip()
    # Tentar mapeamento direto
    if setor in SETOR_TO_SEGMENT:
        return SETOR_TO_SEGMENT[setor]
    # Tentar case-insensitive
    for key, value in SETOR_TO_SEGMENT.items():
        if key.lower() == setor.lower():
            return value
    return None


def import_funds_from_excel(excel_path: str):
    """
    Importa FIIs de um arquivo Excel
    """
    app = create_app()
    with app.app_context():
        # Mapear nomes de segmentos para IDs
        segments_by_name = {s.name: s.id for s in Segment.query.all()}
        
        # Ler Excel
        print(f"Lendo arquivo: {excel_path}")
        df = pd.read_excel(excel_path)
        
        print(f"Total de linhas no Excel: {len(df)}")
        print(f"Colunas encontradas: {list(df.columns)}")
        
        created = 0
        updated = 0
        errors = []
        skipped = 0
        
        for idx, row in df.iterrows():
            # Extrair código do FII
            fund_code = None
            for col in ["codigo_negociacao", "ticker", "codigo"]:
                if col in df.columns and pd.notna(row.get(col)):
                    fund_code = str(row[col]).strip().upper()
                    break
            
            if not fund_code:
                skipped += 1
                continue
            
            # Extrair nome do fundo
            name = None
            for col in ["nome_pregao", "nome_capitania", "razao_social", "nome"]:
                if col in df.columns and pd.notna(row.get(col)):
                    name = str(row[col]).strip()
                    break
            
            if not name:
                errors.append(f"FII {fund_code} sem nome")
                continue
            
            # Extrair setor/segmento
            segment_name = None
            if "setor" in df.columns and pd.notna(row.get("setor")):
                setor = str(row["setor"]).strip()
                segment_name = normalize_segment_name(setor)
            
            segment_id = None
            if segment_name:
                segment_id = segments_by_name.get(segment_name)
                if not segment_id:
                    errors.append(f"Segmento '{segment_name}' nao encontrado para {fund_code} (setor original: {row.get('setor', 'N/A')})")
            
            # Buscar ou criar fundo
            fund = Fund.query.filter_by(fund_code=fund_code).first()
            
            if fund:
                # Atualizar existente
                fund.name = name
                if segment_id:
                    fund.segment_id = segment_id
                fund.updated_at = datetime.utcnow()
                updated += 1
            else:
                # Criar novo
                fund = Fund(
                    fund_code=fund_code,
                    name=name,
                    segment_id=segment_id
                )
                db.session.add(fund)
                created += 1
        
        db.session.commit()
        
        print(f"\nImportacao concluida:")
        print(f"  - Criados: {created}")
        print(f"  - Atualizados: {updated}")
        print(f"  - Ignorados (sem codigo): {skipped}")
        if errors:
            print(f"  - Erros: {len(errors)}")
            for error in errors[:20]:  # Mostrar apenas os 20 primeiros
                print(f"    {error}")
            if len(errors) > 20:
                print(f"    ... e mais {len(errors) - 20} erros")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_funds_excel.py <caminho_do_excel>")
        print("Excel deve ter colunas: codigo_negociacao (ou ticker), nome_pregao (ou nome_capitania), setor")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    if not os.path.exists(excel_path):
        print(f"Arquivo nao encontrado: {excel_path}")
        sys.exit(1)
    
    import_funds_from_excel(excel_path)
