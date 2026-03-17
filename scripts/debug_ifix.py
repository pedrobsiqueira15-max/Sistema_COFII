import csv
import os
import sys
from urllib.request import urlopen

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import create_app
from app.extensions import db
from app.models import IFIXComposition, Fund

def download_csv(url: str) -> str:
    with urlopen(url) as response:
        data = response.read()
        # Tentar diferentes codificações
        for encoding in ["utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        # Se nenhuma funcionar, usar latin-1 como fallback
        return data.decode("latin-1", errors="ignore")

def debug_ifix_column(url: str):
    """Debug para verificar qual coluna contém a composição do IFIX"""
    csv_text = download_csv(url)
    reader = csv.DictReader(csv_text.splitlines())
    
    print("Colunas encontradas no datafeed:")
    for i, col in enumerate(reader.fieldnames):
        print(f"  {i+1}. {col}")
        if "comp" in col.lower() or "carteira" in col.lower() or "ifix" in col.lower() or "ind" in col.lower():
            print(f"     *** POSSIVEL COLUNA DO IFIX ***")
    
    print("\n" + "="*80)
    print("Procurando coluna com 'Comp carteira' e 'Ind Fdo Imob':")
    ifix_header = next((h for h in reader.fieldnames if "Comp carteira" in h and "Ind Fdo Imob" in h), None)
    if ifix_header:
        print(f"  Encontrada: {ifix_header}")
    else:
        print("  NÃO ENCONTRADA!")
        print("\nTentando outras variações:")
        for h in reader.fieldnames:
            if "comp" in h.lower() or "carteira" in h.lower():
                print(f"    - {h}")
    
    print("\n" + "="*80)
    print("Primeiras linhas com dados do IFIX:")
    csv_text2 = download_csv(url)
    reader2 = csv.DictReader(csv_text2.splitlines())
    count = 0
    ifix_col = "Comp carteira|Mais Recente|em %|Ind Fdo Imob"
    for row in reader2:
        if count >= 10:
            break
        fund_code = row.get("Código") or row.get("Codigo") or row.get("Cdigo") or ""
        if fund_code:
            value = row.get(ifix_col, "").strip()
            if value and value != "-" and value != "":
                print(f"  {fund_code}: {value}%")
                count += 1

def check_database():
    """Verifica se há dados de IFIX no banco"""
    app = create_app()
    with app.app_context():
        count = IFIXComposition.query.count()
        print(f"\nTotal de registros de IFIX no banco: {count}")
        
        if count > 0:
            from sqlalchemy import func
            latest_date = db.session.query(func.max(IFIXComposition.as_of_date)).scalar()
            print(f"Data mais recente: {latest_date}")
            
            sample = IFIXComposition.query.filter_by(as_of_date=latest_date).limit(5).all()
            print(f"\nAmostra de {len(sample)} registros:")
            for rec in sample:
                fund = Fund.query.filter_by(fund_code=rec.fund_code).first()
                segment = fund.segment.name if fund and fund.segment else "SEM SEGMENTO"
                print(f"  {rec.fund_code} ({segment}): {rec.weight}%")
        else:
            print("Nenhum dado de IFIX encontrado no banco!")

if __name__ == "__main__":
    url = "https://api.data.economatica.com/1/oficial/datafeed/download/1/H04%2FhWKn20%2BrhndJzZtKV%2B8%2FKw1zSj201wQHRs49PdRLLXEDtbW83Ugikb8wcORvGQWg7Q6Ea4i1jk45x1yv0fntvpM8ssb46OfYv5Me1fU8K8dlEBUoUNmgEDdeXBORiYM%2B3rkmFc0NETTNyryAtXvppc0FdSsiyG%2FQbIsDEsBEJitCPD01VdQFDCDO06LG031HAntWtqwrk9FIkhBEj0%2BFPSZkXdIQBrDCNbTe%2BYm1abwYZIBh2%2BrNe4HKxSoUmO4pcwqcj384PE%2B%2BSjAnFnCVPnWnB6iC7s5E8lhRNWyVZGygi9q7mKrsqGQVZkoemlmCGiTvZ13hHMciTUphXw%3D%3D"
    
    print("="*80)
    print("DEBUG: Verificando coluna do IFIX no datafeed")
    print("="*80)
    debug_ifix_column(url)
    
    print("\n" + "="*80)
    print("DEBUG: Verificando banco de dados")
    print("="*80)
    check_database()
