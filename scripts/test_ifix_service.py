import os
import sys

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import create_app
from app.services import get_latest_ifix_composition_by_segment

app = create_app()
with app.app_context():
    ifix_date, ifix_alloc = get_latest_ifix_composition_by_segment()
    
    print(f"Data: {ifix_date}")
    print(f"Total de segmentos: {len(ifix_alloc)}")
    print("\nComposição do IFIX por segmento:")
    for segment, weight in sorted(ifix_alloc.items()):
        print(f"  {segment}: {weight}%")
    
    total = sum(ifix_alloc.values())
    print(f"\nTotal: {total}%")
