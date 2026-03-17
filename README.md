# Sistema COFII

Sistema web em Python para coletar pesos de segmentos de FIIs por analista,
calcular a alocacao media da equipe, comparar com IFIX e calcular indicadores
ponderados da carteira com base em um datafeed (Economatica).

## Objetivos iniciais
- Login de analistas com usuario e senha
- Segmentos pre-definidos com validacao de soma 100%
- Calculo da alocacao media semanal por segmento
- Visualizacao do peso atual da carteira e do IFIX
- Historico de alocacoes ao longo do tempo
- Importacao de indicadores por fundo e calculo de medias ponderadas

## Requisitos
- Python 3.11+

## Instalar dependencias
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Inicializar o banco
```bash
set ADMIN_EMAIL=admin@cofii.local
set ADMIN_PASSWORD=admin123
python scripts\init_db.py
```

## Criar novos usuarios
```bash
python scripts\create_user.py analista@cofii.local "Analista 1" senha123
```

## Executar o app
```bash
python run.py
```

Depois acesse: http://127.0.0.1:5000

## Datafeed (Economatica)
Importe indicadores por fundo:
```bash
python scripts\import_economatica.py data\economatica.csv
```

Importe direto do link do datafeed (CSV diario) — **preenche indicadores e composição do IFIX**:
```bash
python scripts\import_economatica_url.py
```
(Sem argumentos usa a URL padrão; ou passe a URL como argumento. Para Supabase, defina `DATABASE_URL` antes de rodar.)

Importe composicao da carteira:
```bash
python scripts\import_portfolio.py data\carteira.csv
```

Importe os pesos do IFIX por segmento:
```bash
python scripts\import_benchmark.py data\ifix.csv
```

Os arquivos CSV devem ter as colunas basicas:
- economatica.csv: fund_code, as_of_date, dy_12m, volatility, leverage, beta, p_vp
- carteira.csv: fund_code, segment, as_of_date, weight
- ifix.csv: segment, as_of_date, weight

