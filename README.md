# Melchior — JackBot Predictive Analytics

Sistema de predição de eventos em partidas de futebol ao vivo, composto por um serviço Java de orquestração e um serviço Python de inferência baseado em aprendizado de máquina.

---

## Visão geral

O **Delfos** é o serviço de ML do Melchior. Ele treina modelos com dados históricos do StatsBomb Open Data (3.500+ partidas, 75+ competições) e expõe uma API REST para predições em tempo real integrada com a BetsAPI (Bet365).

### O que o sistema prediz

| Predição | Modelo | Status |
|---|---|---|
| Resultado final (Casa / Empate / Fora) | XGBClassifier | Pendente — bug exportação ONNX |
| Total de gols | GradientBoostingRegressor | Operacional |
| Total de escanteios | GradientBoostingRegressor / PoissonRegressor | Operacional |
| Total de cartões amarelos | GradientBoostingRegressor / PoissonRegressor | Operacional |
| Total de cartões vermelhos | GradientBoostingRegressor / PoissonRegressor | Operacional |

Todos os modelos usam estatísticas do **1º tempo** para predizer o jogo completo. O fluxo principal é: Java recebe um jogo ao vivo → envia o `fi` (fixture ID da BetsAPI) para o Delfos → Delfos busca os dados, normaliza e retorna as probabilidades.

---

## Estrutura do repositório

```
Melchior/
├── delfos/                        # Serviço de ML (Python / FastAPI)
│   ├── api/
│   │   ├── app.py                 # Aplicação FastAPI
│   │   ├── routers/
│   │   │   ├── health.py          # GET /health
│   │   │   ├── predictions.py     # POST /v1/predict/*
│   │   │   └── betsapi.py         # POST /v1/predict/betsapi/*
│   │   ├── schemas/
│   │   │   ├── request.py         # LiveMatchRequest, PredictionRequest
│   │   │   └── response.py        # MatchOutcomeResponse, etc.
│   │   └── services/
│   │       ├── inference.py       # Lógica de inferência ONNX
│   │       ├── model_registry.py  # Carrega sessões ONNX do manifest
│   │       ├── feature_store.py   # Lookup por match_id + normalização live
│   │       ├── betsapi_client.py  # HTTP async para a BetsAPI
│   │       └── betsapi_mapper.py  # Mapeia JSON BetsAPI → LiveMatchRequest
│   ├── training/
│   │   ├── train_match_outcome.py
│   │   ├── train_total_goals.py
│   │   ├── train_corners.py
│   │   ├── train_cards.py
│   │   └── train_player_sog.py
│   └── serialization/
│       └── export_models.py       # Exporta modelos MLflow → ONNX
├── etl/
│   ├── statsbomb_loader.py        # StatsBomb JSON → CSV com features HT
│   ├── data_loader.py             # Lê CSVs gerados
│   ├── cleaner.py                 # Limpeza e validação
│   ├── feature_engineer.py        # Derivações (diff, competição)
│   └── preprocessor.py            # StandardScaler + split 90/10 + parquet
├── data/
│   ├── raw/                       # CSVs gerados pelo statsbomb_loader
│   └── processed/                 # Parquets normalizados (train + holdout)
├── models/
│   ├── onnx/                      # Arquivos .onnx + model_manifest.json
│   └── preprocessors/             # Scalers .pkl para os endpoints /live/*
├── docs/
│   ├── Delfos_API.postman_collection.json
│   ├── architecture.md
│   ├── api_reference.md
│   └── pipeline.md
├── run_pipeline.py                # Roda ETL + treinamento completo
├── run_api.sh                     # Inicia a API com checagem de dependências
├── requirements-ml.txt
└── .env                           # Variáveis de ambiente (não commitado)
```

---

## Pré-requisitos

- Python 3.11+
- Java 17+ (para o predictive-service)
- Token de API da BetsAPI (Bet365)

---

## Instalação

```bash
# Clone o repositório
git clone <url-do-repo>
cd Melchior

# Instale as dependências Python
pip install -r requirements-ml.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env e adicione seu BETSAPI_TOKEN
```

### Arquivo `.env`

```env
# Predictive Service (Java)
PREDICTIVE_PORT=8080
SPRING_PROFILES_ACTIVE=dev
CORS_ALLOWED_ORIGINS=http://localhost:5173

# Delfos API (Python)
BETSAPI_TOKEN=seu_token_aqui
DELFOS_PORT=8000
DELFOS_HOST=0.0.0.0
```

---

## Pipeline de treinamento

Execute o pipeline completo (ETL + treinamento + avaliação):

```bash
python run_pipeline.py
```

Ou pule o ETL se os parquets já existem:

```bash
python run_pipeline.py --skip-etl
```

Depois exporte os modelos para ONNX:

```bash
python -m delfos.serialization.export_models
```

Os artefatos ficam em:
- `models/onnx/` — arquivos `.onnx` + `model_manifest.json`
- `models/preprocessors/` — scalers `.pkl`
- `mlflow.db` — tracking de experimentos (visualize com `mlflow ui --backend-store-uri sqlite:///mlflow.db`)

---

## Rodando a API

```bash
bash run_api.sh
```

O script verifica dependências, valida o manifest ONNX e sobe o uvicorn. Por padrão, a API fica disponível em `http://localhost:8000`.

Docs interativos (Swagger UI): `http://localhost:8000/docs`

---

## Endpoints principais

### Saúde

```
GET /health
```

### Predição via BetsAPI (uso principal — jogo ao vivo)

```
POST /v1/predict/betsapi/total-goals
POST /v1/predict/betsapi/corners
POST /v1/predict/betsapi/cards
POST /v1/predict/betsapi/match-outcome   ← pendente
```

Body:
```json
{
  "fi": "12345678",
  "competition_type": "Domestic League"
}
```

Como obter o `fi` de um jogo ao vivo:
```
GET https://api.b365api.com/v1/bet365/inplay?token=SEU_TOKEN
```
Procure `sport_id=1` (futebol) e copie o campo `fi` do evento desejado.

### Predição histórica (para testes)

```
POST /v1/predict/total-goals   {"match_id": "3829431"}
POST /v1/predict/corners       {"match_id": "3829431"}
POST /v1/predict/cards         {"match_id": "3829431"}
```

### Predição com features manuais

```
POST /v1/predict/live/total-goals
POST /v1/predict/live/corners
POST /v1/predict/live/cards
```

Body (estatísticas acumuladas do 1º tempo):
```json
{
  "competition_type": "Domestic League",
  "ht_goals_home": 1,
  "ht_goals_away": 0,
  "ht_shots_home": 6,
  "ht_shots_away": 3,
  "ht_sog_home": 3,
  "ht_sog_away": 1,
  "ht_fouls_home": 5,
  "ht_fouls_away": 7,
  "ht_corners_home": 4,
  "ht_corners_away": 2,
  "ht_yellow_cards_home": 1,
  "ht_yellow_cards_away": 2
}
```

---

## Respostas de exemplo

**Total de gols:**
```json
{
  "expected_goals": 2.45,
  "over_25_probability": 0.44,
  "under_25_probability": 0.56,
  "most_likely_range": "2-3",
  "confidence_score": 0.56,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T09:26:54Z"
}
```

**Cartões:**
```json
{
  "expected_yellow_cards": 4.90,
  "expected_red_cards": 0.09,
  "over_3_yellow_probability": 0.68,
  "under_3_yellow_probability": 0.32,
  "confidence_score": 0.68,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T09:26:54Z"
}
```

---

## Códigos HTTP

| Código | Significado |
|---|---|
| 200 | Predição realizada com sucesso |
| 400 | match_id não numérico |
| 404 | match_id ou fi não encontrado |
| 422 | Jogo fora da janela HT (2º tempo ou encerrado) |
| 503 | Modelo não carregado ou BetsAPI indisponível |

---

## Documentação técnica

| Documento | Descrição |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Arquitetura do sistema e fluxo de dados |
| [docs/api_reference.md](docs/api_reference.md) | Referência completa de todos os endpoints |
| [docs/pipeline.md](docs/pipeline.md) | Pipeline ETL e treinamento dos modelos |
| [docs/Delfos_API.postman_collection.json](docs/Delfos_API.postman_collection.json) | Collection Postman para testes |

---

## Limitações conhecidas

- **match_outcome** retorna HTTP 503: o modelo XGBClassifier não pôde ser exportado para ONNX por incompatibilidade entre XGBoost 3.2 e onnxmltools 1.16 (nós de split binário sem `split_condition` no dump JSON). Correção: retreinar com GradientBoostingClassifier do scikit-learn.
- Os modelos foram treinados com dados do StatsBomb Open Data, que cobre principalmente ligas europeias de elite. Partidas de ligas menores podem ter menor precisão.
- O token da BetsAPI precisa ter permissão para o endpoint `/v1/bet365/inplay_stats`.
