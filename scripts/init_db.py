import os
import sys

# Adicionar o diretório raiz ao PYTHONPATH
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _root)
os.chdir(_root)

# Carregar .env (DATABASE_URL para Supabase, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.main import create_app
from app.extensions import db
from app.models import Segment, User, IFIXComposition


DEFAULT_SEGMENTS = [
    "Logística",
    "Lajes Corporativas",
    "Shoppings",
    "CRI",
    "Residencial",
    "Híbrido",
    "FOF",
    "Renda Urbana",
    "Outros",
]

SEGMENT_RENAMES = {
    "Logistica": "Logística",
    "Hibrido": "Híbrido",
    "Fundo de Fundos": "FOF",
}


def normalize_segments():
    """Garante que os nomes de segmentos estejam atualizados."""
    existing_by_name = {s.name: s for s in Segment.query.all()}

    # Renomear antigos
    for old, new in SEGMENT_RENAMES.items():
        seg = existing_by_name.get(old)
        if seg:
            seg.name = new

    db.session.flush()

    # Garantir todos os segmentos padrão
    existing_names = {s.name for s in Segment.query.all()}
    for name in DEFAULT_SEGMENTS:
        if name not in existing_names:
            db.session.add(Segment(name=name))

    db.session.commit()


def seed_admin_user():
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    name = os.environ.get("ADMIN_NAME", "Admin COFII")
    if not email or not password:
        print("ADMIN_EMAIL e ADMIN_PASSWORD nao definidos. Usuario admin nao criado.")
        return
    if User.query.filter_by(email=email).first():
        print("Usuario admin ja existe.")
        return
    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print("Usuario admin criado.")


def seed_default_analysts():
    """Cria os analistas padrao, usados apenas para selecao na tela."""
    default_analysts = [
        ("pedro@cofii.local", "Pedro"),
        ("ricardo@cofii.local", "Ricardo"),
        ("enzo@cofii.local", "Enzo"),
        ("reinaldo@cofii.local", "Reinaldo"),
    ]
    for email, name in default_analysts:
        if not User.query.filter_by(email=email).first():
            user = User(email=email, name=name)
            # Senha dummy, pois login esta desativado
            user.set_password("changeme")
            db.session.add(user)
    db.session.commit()


def main():
    import sys
    try:
        app = create_app()
        with app.app_context():
            try:
                print("Criando tabelas...")
                db.create_all()
                print("Tabelas criadas com sucesso.")
                normalize_segments()
                print("Segmentos normalizados.")
                seed_default_analysts()
                print("Analistas padrao criados (se necessario).")
                seed_admin_user()
                # Se ainda não há dados do IFIX/indicadores, importar do datafeed (Supabase/Render)
                if IFIXComposition.query.count() == 0:
                    print("Tabelas ifix/indicadores vazias. Importando datafeed Economatica...")
                    try:
                        sys.path.insert(0, os.path.join(_root, "scripts"))
                        import import_economatica_url
                        import_economatica_url.import_from_url(import_economatica_url.DEFAULT_DATAFEED_URL)
                        print("Datafeed importado: ifix_composition e fund_metrics.")
                    except Exception as e_import:
                        print(f"AVISO: Falha ao importar datafeed (continuando): {e_import}", file=sys.stderr)
                print("Inicializacao concluida.")
            except Exception as e:
                print(f"AVISO: Erro ao inicializar banco (continuando mesmo assim): {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Não fazer exit(1) - deixar o servidor subir mesmo se houver erro
    except Exception as e:
        print(f"ERRO CRITICO ao criar app: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
