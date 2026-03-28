# Delfos v1.0 — Arquitetura do Sistema

## Visão macro

```
┌─────────────┐        fi (fixture ID)        ┌──────────────────────────┐
│   Frontend  │ ─────────────────────────────► │  Predictive Service      │
│  (React)    │ ◄─────────────────────────────  │  (Java / Spring Boot)    │
└─────────────┘      probabilidades JSON        └────────────┬─────────────┘
                                                             │  POST /v1/predict/betsapi/*
                                                             │  {"fi": "12345678"}
                                                             ▼
                                                ┌──────────────────────────┐
                                                │  Delfos API              │
                                                │  (Python / FastAPI)      │
                                                │  :8000                   │
                                                └────────────┬─────────────┘
                                                             │
                          ┌──────────────────────────────────┼────────────────────────┐
                          │                                  │                        │
                          ▼                                  ▼                        ▼
               ┌──────────────────┐             ┌────────────────────┐   ┌────────────────────┐
               │  BetsAPI Client  │             │  Model Registry    │   │  Feature Store     │
               │  (httpx async)   │             │  (ONNX sessions)   │   │  (parquets +       │
               │                  │             │                    │   │   scalers)         │
               │  Bet365 API      │             │  total_goals.onnx  │   │                    │
               │  /inplay_stats   │             │  corners.onnx      │   │  team_outcome.pqt  │
               └────────┬─────────┘             │  yellow_cards.onnx │   │  team_sog.pqt      │
                        │ stats JSON            │  red_cards.onnx    │   │  scaler_*.pkl      │
                        ▼                        └────────────────────┘   └────────────────────┘
               ┌──────────────────┐
               │  BetsAPI Mapper  │
               │                  │
               │  on_target → sog │
               │  on_target +     │
               │  off_target →    │
               │  total shots     │
               │                  │
               │  assert_period   │
               │  (1, HT only)    │
               └────────┬─────────┘
                        │ LiveMatchRequest
                        ▼
               ┌──────────────────┐
               │  Inference       │
               │                  │
               │  normalize →     │
               │  build_input →   │
               │  run ONNX →      │
               │  format response │
               └──────────────────┘
```

---

## Componentes

### Delfos API (`delfos/api/`)

**`app.py`**
Inicialização do FastAPI. No startup (`lifespan`):
1. `ModelRegistry.load_all()` — carrega todas as sessões ONNX em memória
2. `FeatureStore.load()` — carrega os parquets e scalers em memória

Middleware CORS configurado para aceitar requisições do `CORS_ALLOWED_ORIGIN` (default: `http://predictive-service:8080`).

**Routers:**

| Router | Prefixo | Descrição |
|---|---|---|
| `health.py` | `/health` | Status da API |
| `predictions.py` | `/v1/predict` | Histórico + live manual |
| `betsapi.py` | `/v1/predict/betsapi` | Integração automática BetsAPI |

---

### Model Registry (`services/model_registry.py`)

Lê o `models/onnx/model_manifest.json` no startup e cria sessões `onnxruntime.InferenceSession` em memória para cada modelo. Se um arquivo `.onnx` não for encontrado, o endpoint retorna 503 em vez de falhar na inicialização.

Modelos monitorados: `match_outcome`, `total_goals`, `corners`, `yellow_cards`, `red_cards`

---

### Feature Store (`services/feature_store.py`)

Carrega dois conjuntos de parquets (train + holdout combinados):

| Granularidade | Arquivo | Colunas principais |
|---|---|---|
| `team_outcome` | `team_outcome_{split}.parquet` | ht_goals_diff, ht_shots_diff, ht_sog_diff, ht_fouls_diff, ht_corners_*, ht_yellow_* |
| `team_sog` | `team_sog_{split}.parquet` | ht_shots_home/away, ht_sog_home/away, ht_goals_home/away |

Também carrega os scalers `models/preprocessors/scaler_{gran}.pkl` para normalização dos endpoints `/live/*` e `/betsapi/*`.

**Normalização live:**
```
valor_normalizado = (valor_bruto - scaler.mean_[i]) / scaler.scale_[i]
```
Features que não estão no scaler (como `competition_type`) passam sem transformação.

---

### BetsAPI Client (`services/betsapi_client.py`)

```
GET https://api.b365api.com/v1/bet365/inplay_stats?token=TOKEN&FI=fi
```

- Timeout: 10 segundos
- Sem retry (responsabilidade do caller Java)
- Token lido de `BETSAPI_TOKEN` (variável de ambiente, carregada do `.env` via python-dotenv)

Exceções:
- `BetsAPIUnavailableError` → HTTP 503
- `BetsAPIMatchNotFoundError` → HTTP 404

---

### BetsAPI Mapper (`services/betsapi_mapper.py`)

Mapeamento de campos BetsAPI → `LiveMatchRequest`:

| Campo BetsAPI | Feature do modelo | Observação |
|---|---|---|
| `stats.on_target` (home) | `ht_sog_home` | |
| `stats.on_target` (away) | `ht_sog_away` | |
| `stats.on_target + off_target` (home) | `ht_shots_home` | BetsAPI não tem "total shots" |
| `stats.on_target + off_target` (away) | `ht_shots_away` | |
| `stats.corners` (home) | `ht_corners_home` | |
| `stats.corners` (away) | `ht_corners_away` | |
| `stats.yellow_cards` (home) | `ht_yellow_cards_home` | |
| `stats.yellow_cards` (away) | `ht_yellow_cards_away` | |
| `stats.fouls` (home) | `ht_fouls_home` | |
| `stats.fouls` (away) | `ht_fouls_away` | |
| `scores.home` | `ht_goals_home` | |
| `scores.away` | `ht_goals_away` | |
| `BetsAPIRequest.competition_type` | `competition_type` | passado pelo cliente |

**Validação de período (`timer.q`):**

| Valor | Período | Aceito? |
|---|---|---|
| `"1"` | 1º tempo em andamento | Sim |
| `"HT"` | Intervalo | Sim (janela ideal) |
| `"1H"`, `"45"` | Variantes do 1º tempo | Sim |
| `"2"`, `"2H"` | 2º tempo | Não — HTTP 422 |
| `"FT"`, `"ET"`, `"P"` | Final / prorrogação / pênaltis | Não — HTTP 422 |

---

### Inference (`services/inference.py`)

Fluxo para predição histórica:
1. Busca a linha do `match_id` no FeatureStore
2. Seleciona as features numéricas do modelo
3. Aplica `pd.get_dummies` no `competition_type`
4. Alinha colunas com `feature_names` do manifest (via `reindex`)
5. Converte para `np.float32` e executa `session.run()`
6. Formata resposta com métricas derivadas (Poisson para over/under)

Fluxo para predição live (BetsAPI):
1. Converte `LiveMatchRequest` → `pd.Series` com colunas diff derivadas
2. Normaliza via scaler do FeatureStore
3. Mesmo fluxo a partir do passo 2 acima

**Features por modelo:**

```
match_outcome:  ht_goals_diff, ht_shots_diff, ht_sog_diff, ht_fouls_diff
total_goals:    ht_shots_home, ht_shots_away, ht_sog_home, ht_sog_away,
                ht_goals_home, ht_goals_away
corners:        ht_shots_home, ht_shots_away, ht_fouls_home, ht_fouls_away,
                ht_corners_home, ht_corners_away
cards:          ht_fouls_home, ht_fouls_away,
                ht_yellow_cards_home, ht_yellow_cards_away

Todos + competition_type (one-hot encoded: Domestic League, World Cup, Continental)
```

**Cálculo de over/under via Poisson:**
```python
P(X > threshold) = 1 - CDF_Poisson(floor(threshold), lambda=expected_value)
```

---

## Pipeline de dados

```
StatsBomb JSON
     │
     ▼
statsbomb_loader.py
  - extrai eventos de chute (period=1 → features ht_*)
  - calcula: shots, sog, fouls, corners, yellow_cards, goals por equipe
  - gera: data/raw/comp{id}_s{id}_*.csv
     │
     ▼
data_loader.py → cleaner.py → feature_engineer.py
  - carrega CSVs, limpa nulos, deriva competition_type
     │
     ▼
preprocessor.py
  - split 90/10 estratificado por competition_type
  - StandardScaler fit no treino, aplicado no holdout
  - salva: data/processed/{gran}_{split}.parquet
  - salva: models/preprocessors/scaler_{gran}.pkl
     │
     ▼
training/train_*.py
  - GridSearchCV com 5-fold CV
  - avalia no holdout (MAE para regressores, accuracy para classifier)
  - registra no MLflow (sqlite:///mlflow.db)
  - faz log do modelo no MLflow Model Registry
     │
     ▼
export_models.py
  - carrega cada modelo do MLflow Registry (stage=None, versão mais recente)
  - converte para ONNX via skl2onnx
  - salva: models/onnx/{nome}_v1.0.0.onnx
  - gera: models/onnx/model_manifest.json
```

---

## Decisões de design

**Por que usar apenas dados do 1º tempo?**
Os modelos são chamados no intervalo (ou durante o 1º tempo via BetsAPI). Dados do 2º tempo só estão disponíveis depois que o jogo acaba — inutilizáveis para predição em tempo real.

**Por que ONNX em vez de executar o modelo Python diretamente?**
ONNX desacopla o runtime de inferência do runtime de treinamento. A API pode rodar sem scikit-learn/XGBoost instalados, e as sessões `InferenceSession` têm latência de inferência mais baixa.

**Por que o scaler fica separado do ONNX?**
Os parquets já saem normalizados do ETL — os modelos foram treinados com dados normalizados. Para endpoints históricos, não há necessidade de normalizar na inferência. Para endpoints live (BetsAPI), o scaler é aplicado em Python antes de passar para o ONNX, evitando reempacotar o pipeline inteiro.

**Por que não há retry na BetsAPI?**
A responsabilidade de retry fica no Java Predictive Service, que conhece a lógica de negócio (quantas tentativas, backoff). O Delfos é stateless e focado em inferência.
