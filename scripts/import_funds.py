import csv
import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import create_app
from app.extensions import db
from app.models import Fund, Segment


def import_funds_from_csv(csv_path: str):
    """
    Importa FIIs de um CSV com colunas: fund_code, name, segment
    """
    app = create_app()
    with app.app_context():
        # Mapear nomes de segmentos para IDs
        segments_by_name = {s.name: s.id for s in Segment.query.all()}
        
        created = 0
        updated = 0
        errors = []
        
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                fund_code = row.get("fund_code", "").strip().upper()
                name = row.get("name", "").strip()
                segment_name = row.get("segment", "").strip()
                
                if not fund_code:
                    errors.append(f"Linha sem fund_code: {row}")
                    continue
                
                if not name:
                    errors.append(f"FII {fund_code} sem nome")
                    continue
                
                # Buscar ou criar fundo
                fund = Fund.query.filter_by(fund_code=fund_code).first()
                
                segment_id = None
                if segment_name:
                    segment_id = segments_by_name.get(segment_name)
                    if not segment_id:
                        errors.append(f"Segmento '{segment_name}' nao encontrado para {fund_code}")
                
                if fund:
                    # Atualizar existente
                    fund.name = name
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
        
        print(f"Importacao concluida:")
        print(f"  - Criados: {created}")
        print(f"  - Atualizados: {updated}")
        if errors:
            print(f"  - Erros: {len(errors)}")
            for error in errors[:10]:  # Mostrar apenas os 10 primeiros
                print(f"    {error}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_funds.py <caminho_do_csv>")
        print("CSV deve ter colunas: fund_code, name, segment")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Arquivo nao encontrado: {csv_path}")
        sys.exit(1)
    
    import_funds_from_csv(csv_path)
