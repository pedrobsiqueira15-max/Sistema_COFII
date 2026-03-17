import os
import sys
from urllib.request import urlopen

# Adicionar o diretório raiz ao PYTHONPATH
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_script_dir, ".."))
sys.path.insert(0, _root)
os.chdir(_root)

# Carregar .env para usar DATABASE_URL do Supabase quando rodar localmente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.main import create_app
from app.datafeed_import import import_datafeed_from_csv_text


def download_csv(url: str) -> str:
    with urlopen(url) as response:
        data = response.read()
        for encoding in ["utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("latin-1", errors="ignore")


def import_from_url(url: str):
    csv_text = download_csv(url)
    app = create_app()
    with app.app_context():
        num_metrics, num_ifix = import_datafeed_from_csv_text(csv_text)
        print(f"Importacao concluida: {num_metrics} indicadores e {num_ifix} pesos do IFIX.")


# URL padrão do datafeed Economatica (pode ser sobrescrita por env ou argumento)
DEFAULT_DATAFEED_URL = os.environ.get(
    "ECONOMATICA_DATAFEED_URL",
    "https://api.data.economatica.com/1/oficial/datafeed/download/1/H04%2FhWKn20%2BrhndJzZtKV%2B8%2FKw1zSj201wQHRs49PdRLLXEDtbW83Ugikb8wcORvGQWg7Q6Ea4i1jk45x1yv0fntvpM8ssb46OfYv5Me1fU8K8dlEBUoUNmgEDdeXBORiYM%2B3rkmFc0NETTNyryAtXvppc0FdSsiyG%2FQbIsDEsBEJitCPD01VdQFDCDO06LG031HAntWtqwrk9FIkhBEj0%2BFPSZkXdIQBrDCNbTe%2BYm1abwYZIBh2%2BrNe4HKxSoUmO4pcwqcj384PE%2B%2BSjAnFnCVPnWnB6iC7s5E8lhRNWyVZGygi9q7mKrsqGQVZkoemlmCGiTvZ13hHMciTUphXw%3D%3D",
)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_DATAFEED_URL
    if not url or url.strip() == "":
        print("Uso: python scripts/import_economatica_url.py [url]")
        print("  ou defina ECONOMATICA_DATAFEED_URL no ambiente.")
        sys.exit(1)
    print(f"Importando de: {url[:80]}...")
    import_from_url(url.strip())
