# Delfos v1.0 — Fluxo Técnico Detalhado

> Documento de referência para desenvolvimento e integração.
> Cobre o fluxo completo desde a coleta dos dados até a resposta HTTP da API.

---

## Índice

1. [Visão do Sistema](#1-visão-do-sistema)
2. [Fluxo Completo — Diagrama](#2-fluxo-completo--diagrama)
3. [Fluxo do Modelo](#3-fluxo-do-modelo)
   - 3.1 [Coleta — StatsBomb JSON → CSV](#31-coleta--statsbomb-json--csv)
   - 3.2 [Carregamento e Limpeza](#32-carregamento-e-limpeza)
   - 3.3 [Engenharia de Features](#33-engenharia-de-features)
   - 3.4 [Preprocessamento — Split e Normalização](#34-preprocessamento--split-e-normalização)
   - 3.5 [Treinamento dos Modelos](#35-treinamento-dos-modelos)
   - 3.6 [Avaliação no Holdout](#36-avaliação-no-holdout)
   - 3.7 [Exportação ONNX](#37-exportação-onnx)
4. [Fluxo da API](#4-fluxo-da-api)
   - 4.1 [Inicialização](#41-inicialização)
   - 4.2 [Request → Inferência → Response](#42-request--inferência--response)
   - 4.3 [Endpoints em Detalhe](#43-endpoints-em-detalhe)
   - 4.4 [Tratamento de Erros](#44-tratamento-de-erros)
5. [Contrato com o Melchior](#5-contrato-com-o-melchior)
6. [Decisões Técnicas Relevantes](#6-decisões-técnicas-relevantes)

---

## 1. Visão do Sistema

O Delfos é um microsserviço Python que:
1. **Treina** modelos de ML com dados históricos do StatsBomb (75 competições, ~5.000 partidas)
2. **Exporta** os modelos treinados para formato ONNX
3. **Serve** predições via API FastAPI consumida pelo Melchior (Spring Boot)

```
StatsBomb Open Data
      │
      ▼
[Pipeline de Treinamento]  ──►  models/onnx/*.onnx
      │                          model_manifest.json
      │
      ▼
[API FastAPI :8000]  ◄──  Melchior :8080  ◄──  Usuário
```

---

## 2. Fluxo Completo — Diagrama

```
┌─────────────────────────────────────────────────────────────────┐
│                     PIPELINE DE TREINAMENTO                      │
│                                                                   │
│  statsbomb_loader.py                                              │
│  ┌─────────────────────────────────────────────┐                 │
│  │  sb.competitions() → 75 competições          │                 │
│  │  sb.matches()      → partidas por competição │                 │
│  │  sb.events()       → eventos de cada partida │                 │
│  │                                               │                 │
│  │  Extrai:  team_outcome / team_sog / player_sog│                 │
│  │  Salva:   data/raw/{ctx}_{gran}.csv (231 CSVs)│                 │
│  └─────────────────────────────────────────────┘                 │
│                          │                                        │
│                          ▼                                        │
│  data_loader.py                                                   │
│  ┌────────────────────────────────────┐                          │
│  │  glob("*_team_outcome.csv") → concat│                          │
│  │  glob("*_team_sog.csv")     → concat│                          │
│  │  glob("*_player_sog.csv")   → concat│                          │
│  └────────────────────────────────────┘                          │
│                          │                                        │
│                          ▼                                        │
│  cleaner.py                                                       │
│  ┌────────────────────────────────────┐                          │
│  │  Remove ht_corners_diff (std=0)    │                          │
│  │  Imputa NaN com mediana da coluna  │                          │
│  └────────────────────────────────────┘                          │
│                          │                                        │
│                          ▼                                        │
│  feature_engineer.py                                              │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  competition_type: mapeado se ausente                   │      │
│  │  player_id_x_world_cup: player_id se WC, senão 0        │      │
│  └────────────────────────────────────────────────────────┘      │
│                          │                                        │
│                          ▼                                        │
│  preprocessor.py                                                  │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  train_test_split(90/10, stratify=competition_type)     │      │
│  │  StandardScaler.fit(train) → transform(train, holdout)  │      │
│  │  NON_SCALE: targets e IDs não são normalizados          │      │
│  │  Salva: {gran}_train.parquet + {gran}_holdout.parquet   │      │
│  │  Salva: scaler_{gran}.pkl                               │      │
│  └────────────────────────────────────────────────────────┘      │
│                          │                                        │
│                          ▼                                        │
│  train_*.py (5 scripts)                                           │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  load_train(gran) → parquet                             │      │
│  │  pd.get_dummies(competition_type)                       │      │
│  │  GridSearchCV(modelo, PARAM_GRID, cv=5)                 │      │
│  │  cv_and_log() → MLflow SQLite                           │      │
│  │  evaluate_regressor/classifier() → plots + CLI          │      │
│  │  Salva: models/trained/{nome}.joblib                    │      │
│  └────────────────────────────────────────────────────────┘      │
│                          │                                        │
│                          ▼                                        │
│  export_models.py                                                 │
│  ┌────────────────────────────────────────────────────────┐      │
│  │  MLflow Registry (SQLite) → load_model()               │      │
│  │  model.n_features_in_ → FloatTensorType dinâmico        │      │
│  │  model.feature_names_in_ → salvo no manifest           │      │
│  │  convert_sklearn() → .onnx                             │      │
│  │  Salva: models/onnx/{nome}_v1.0.0.onnx                  │      │
│  │  Salva: models/onnx/model_manifest.json                 │      │
│  └────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        API FASTAPI :8000                         │
│                                                                   │
│  Startup (lifespan)                                               │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  ModelRegistry.load_all()                            │        │
│  │    → lê model_manifest.json                          │        │
│  │    → rt.InferenceSession(onnx_path) × 5 modelos      │        │
│  │    → armazena feature_names por modelo               │        │
│  │                                                       │        │
│  │  FeatureStore.load()                                  │        │
│  │    → lê team_outcome_train + holdout → índice match_id│        │
│  │    → lê team_sog_train + holdout     → índice match_id│        │
│  └─────────────────────────────────────────────────────┘        │
│                          │                                        │
│                          ▼ (em runtime)                          │
│  POST /v1/predict/{endpoint}                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  PredictionRequest(match_id, season)                 │        │
│  │  int(match_id) → feature_store.get_team_outcome()   │        │
│  │  _build_input() → get_dummies + reindex + float32   │        │
│  │  session.run() → outputs ONNX                        │        │
│  │  Deriva over/under via scipy.stats.poisson.cdf()     │        │
│  │  Response Pydantic → JSON                            │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Fluxo do Modelo

### 3.1 Coleta — StatsBomb JSON → CSV

**Arquivo:** `etl/statsbomb_loader.py`

O StatsBomb disponibiliza eventos de partidas em JSON via API HTTP. O loader itera todas as competições disponíveis e para cada uma:

```
sb.competitions()
    └── para cada (competition_id, season_id):
            sb.matches(cid, sid)
                └── para cada match_id:
                        sb.events(match_id)
                            └── extrai team_outcome, team_sog, player_sog
                                salva: data/raw/{ctx}_{gran}.csv
```

**Context name** gerado por competição:
```
comp{competition_id}_s{season_id}_{nome_sanitizado}_{temporada_sanitizada}
ex: comp43_s106_fifa_world_cup_2022
```

**O que é extraído de sb.events():**

| Campo StatsBomb | Usado em | Como |
|---|---|---|
| `type == "Shot"` | todas granularidades | filtra eventos de chute |
| `shot_outcome` in `{Goal, Saved, Saved To Post}` | todas | define SOG |
| `period == 1` | todas | filtra 1º tempo |
| `team` | team_outcome/sog | identifica home/away |
| `foul_committed_card`, `bad_behaviour_card` | team_outcome | cartões |
| `pass_type == "Corner"` | team_outcome | escanteios |
| `player_id` | player_sog | identifica jogador |
| `type == "Carry"` | player_sog | ht_touches |
| `type == "Dribble"` + `dribble_outcome == "Complete"` | player_sog | ht_dribbles |

**competition_type** definido na extração:
```python
"World Cup"       → "world cup" no nome (exceto feminino e sub-20)
"Domestic League" → "league", "liga", "ligue", "bundesliga", etc.
"Continental"     → demais
```

**Saída:** 231 arquivos CSV em `data/raw/` (3 por competição × ~77 competições).

---

### 3.2 Carregamento e Limpeza

**Arquivos:** `etl/data_loader.py`, `etl/cleaner.py`

**data_loader** usa glob dinâmico:
```python
csv_files = sorted(raw_dir.glob(f"*_{gran}.csv"))
# Extrai source_context do nome do arquivo: {ctx}_{gran}.csv → ctx
# Concatena todos os arquivos da mesma granularidade
```

**cleaner** aplica 2 regras:

| Regra | Afeta | Motivo |
|---|---|---|
| Remove `ht_corners_diff` | `team_outcome` | desvio padrão = 0, sem poder preditivo |
| Imputa NaN com mediana | todas as colunas numéricas | robustez a partidas com dados incompletos |

---

### 3.3 Engenharia de Features

**Arquivo:** `etl/feature_engineer.py`

Apenas para `player_sog`:

**`competition_type`** — mapeada somente se não veio do loader (retrocompatibilidade com dados legados):
```python
if "competition_type" not in df.columns:
    df["competition_type"] = df["source_context"].map({
        "wc2022": "World Cup",
        "ligue1_2021_2022": "Ligue 1"
    }).fillna("Other")
```

**`player_id_x_world_cup`** — feature de interação:
```python
is_wc = source_context.str.contains("wc|world_cup|comp43", case=False)
df["player_id_x_world_cup"] = 0
df.loc[is_wc, "player_id_x_world_cup"] = df.loc[is_wc, "player_id"]
```
Permite ao modelo aprender padrões específicos de jogadores na Copa do Mundo sem confundir com outras competições.

---

### 3.4 Preprocessamento — Split e Normalização

**Arquivo:** `etl/preprocessor.py`

**Split estratificado:**
```
Dataset completo
    └── train_test_split(test_size=0.10, stratify=competition_type, random_state=42)
            ├── 90% → {gran}_train.parquet
            └── 10% → {gran}_holdout.parquet  ← nunca visto durante treino
```

A estratificação garante que a proporção de World Cup / Domestic League / Continental seja igual no treino e no holdout.

**Normalização — anti-leakage:**
```python
scaler = StandardScaler()
scaler.fit(train[numeric_cols])        # aprende média/desvio APENAS do treino
train[numeric_cols]   = scaler.transform(train[numeric_cols])
holdout[numeric_cols] = scaler.transform(holdout[numeric_cols])  # NÃO re-fita
```

**Colunas excluídas da normalização (NON_SCALE):**
```
outcome, total_goals, goals_home_frac, total_corners,
total_red_cards, total_yellow_cards, total_sog,
home_score, away_score, match_id, player_id
```
Targets são excluídos para que o classificador receba inteiros [0, 1, 2] em vez de floats escalonados [-0.95, 0.23, 1.43].

**Saídas:**
```
data/processed/team_outcome_train.parquet
data/processed/team_outcome_holdout.parquet
data/processed/team_sog_train.parquet
data/processed/team_sog_holdout.parquet
data/processed/player_sog_train.parquet
data/processed/player_sog_holdout.parquet
models/preprocessors/scaler_team_outcome.pkl
models/preprocessors/scaler_team_sog.pkl
models/preprocessors/scaler_player_sog.pkl
```

---

### 3.5 Treinamento dos Modelos

**Arquivos:** `delfos/training/train_*.py`

Cada script segue o mesmo padrão:

```python
# 1. Carrega parquet de treino
df = load_train("team_outcome")

# 2. Seleciona features e aplica get_dummies
X = pd.get_dummies(df[FEATURES], columns=["competition_type"])
y = df[TARGET]

# 3. GridSearchCV para encontrar hiperparâmetros ótimos
gs = GridSearchCV(modelo_base, PARAM_GRID, cv=5, scoring=métrica)
gs.fit(X, y)

# 4. CV + log MLflow + salva joblib
scores, model = cv_and_log(gs.best_estimator_, X, y, ...)
```

**Modelos e features por script:**

| Script | Modelo | Features numéricas | Target |
|---|---|---|---|
| `train_match_outcome.py` | XGBoostClassifier | ht_goals_diff, ht_shots_diff, ht_sog_diff, ht_fouls_diff | outcome (0/1/2) |
| `train_total_goals.py` | GBR | ht_shots_home/away, ht_sog_home/away, ht_goals_home/away | total_goals |
| `train_total_goals.py` | GBR | (mesmo) | goals_home_frac |
| `train_corners.py` | GBR ou Poisson* | ht_shots_home/away, ht_fouls_home/away, ht_corners_home/away | total_corners |
| `train_cards.py` | GBR ou Poisson* | ht_fouls_home/away, ht_yellow_cards_home/away | total_red_cards |
| `train_cards.py` | GBR ou Poisson* | (mesmo) | total_yellow_cards |
| `train_player_sog.py` | GBR | ht_passes, ht_touches, ht_dribbles, player_id_x_world_cup | total_sog |

> *Para corners e cartões: treina GBR e PoissonRegressor separadamente, seleciona automaticamente o de menor MAE em CV k=5.

**`pd.get_dummies` sobre competition_type** adiciona 3 colunas binárias ao vetor de features:
```
competition_type_Continental      → 1 se Continental, senão 0
competition_type_Domestic League  → 1 se Domestic League, senão 0
competition_type_World Cup        → 1 se World Cup, senão 0
```

Após `model.fit(X, y)`, o modelo armazena:
- `model.n_features_in_`: número total de features (numéricas + dummies)
- `model.feature_names_in_`: lista ordenada com os nomes das colunas

**MLflow (SQLite local):**
```
Experimento "match-outcome"
    └── Run "xgboost-v1"
            ├── params: {n_estimators: 200, max_depth: 5}
            ├── metrics: {accuracy_mean: 0.52, accuracy_std: 0.03}
            └── artifact: modelo sklearn serializado
```

---

### 3.6 Avaliação no Holdout

**Arquivo:** `delfos/training/evaluate.py`

Após o treino, cada modelo é avaliado nos 10% reservados:

```python
df_holdout = load_holdout("team_outcome")
X_h = pd.get_dummies(df_holdout[FEATURES], columns=["competition_type"])
X_h = X_h.reindex(columns=X.columns, fill_value=0)  # alinha colunas com treino
```

O `reindex` é necessário porque o holdout pode não ter todas as categorias de `competition_type` que existem no treino.

**Outputs CLI por modelo:**

Para classificadores:
```
================================================================
  AVALIAÇÃO — match-outcome  |  Holdout 10%  |  Classificador
================================================================
  Accuracy  : 0.52
  Amostras  : 487

  precision  recall  f1-score  support
  HOME       0.58    0.62      0.60    ...
  DRAW       0.28    0.21      0.24    ...
  AWAY       0.52    0.55      0.53    ...

  Features utilizadas (top-10):
    1. ht_goals_diff                 0.4821
    2. ht_sog_diff                   0.1932
    ...
```

Para regressores:
```
  MAE   : 1.12
  RMSE  : 1.48
  R²    : 0.31
```

**Gráficos gerados em `reports/plots/`:**

| Modelo | Gráficos |
|---|---|
| match-outcome | confusion_matrix, feature_importance |
| total-goals | actual_vs_predicted (scatter + resíduos), feature_importance |
| goals-distribution | actual_vs_predicted, feature_importance |
| corners | actual_vs_predicted, feature_importance |
| red-cards | actual_vs_predicted, feature_importance |
| yellow-cards | actual_vs_predicted, feature_importance |
| player-sog | actual_vs_predicted, feature_importance |

---

### 3.7 Exportação ONNX

**Arquivo:** `delfos/serialization/export_models.py`

```python
# Para cada modelo no MLflow Registry:
model = mlflow.sklearn.load_model(f"models:/{registry_name}/{version}")

n_features   = model.n_features_in_        # dinâmico — inclui dummies
feature_names = model.feature_names_in_.tolist()

initial_type = [("float_input", FloatTensorType([None, n_features]))]
onnx_bytes   = convert_sklearn(model, initial_types=initial_type, target_opset={"": 17})

# Salva .onnx e entrada no manifest
```

**`model_manifest.json` gerado:**
```json
{
  "version": "1.0.0",
  "models": [
    {
      "name": "match_outcome",
      "registry_name": "match-outcome",
      "version": "1.0.0",
      "onnx_path": "models/onnx/match_outcome_v1.0.0.onnx",
      "n_features": 7,
      "feature_names": [
        "ht_goals_diff", "ht_shots_diff", "ht_sog_diff", "ht_fouls_diff",
        "competition_type_Continental",
        "competition_type_Domestic League",
        "competition_type_World Cup"
      ],
      "mlflow_run_id": "abc123...",
      "metrics": {"accuracy_mean": 0.52}
    }
  ]
}
```

**Nota sobre o scaler:** O `StandardScaler` é aplicado no ETL e os parquets já armazenam valores normalizados. Os modelos foram treinados com dados pré-normalizados, portanto os arquivos ONNX esperam entrada já normalizada. A API carrega features diretamente dos parquets, sem necessidade de aplicar o scaler em runtime.

---

## 4. Fluxo da API

### 4.1 Inicialização

**Arquivo:** `delfos/api/app.py`

A inicialização usa `lifespan` (FastAPI moderno), que executa antes do servidor aceitar requests:

```
uvicorn delfos.api.app:app --port 8000
    │
    ▼
lifespan()
    ├── ModelRegistry.load_all()
    │       ├── lê models/onnx/model_manifest.json
    │       ├── para cada modelo em API_MODELS:
    │       │       rt.InferenceSession(onnx_path)  ← sessão ONNX em memória
    │       │       armazena feature_names[modelo]
    │       └── registra manifest_version
    │
    └── FeatureStore.load()
            ├── team_outcome = concat(train.parquet, holdout.parquet)
            │       → set_index("match_id")  ← O(1) lookup por match_id
            └── team_sog = concat(train.parquet, holdout.parquet)
                    → set_index("match_id")
```

Todos os modelos e dados são carregados **uma única vez** na startup. Requests subsequentes não tocam em disco.

Se um arquivo ONNX não existir, o modelo correspondente é omitido do registry e o endpoint retorna 503 em vez de travar a inicialização.

---

### 4.2 Request → Inferência → Response

Fluxo detalhado para qualquer endpoint de predição:

```
POST /v1/predict/match-outcome
Body: {"match_id": "3788741", "season": "2022"}
    │
    ▼
[predictions.py — router]
    │
    ├── Valida schema Pydantic (match_id: str, season: Optional[str])
    │   → 422 se campo ausente ou tipo errado
    │
    ├── int(match_id)
    │   → 400 se não numérico ("abc", "3.14", etc.)
    │
    ▼
[inference.predict_match_outcome(match_id, registry, store)]
    │
    ├── registry.is_loaded("match_outcome")
    │   → RuntimeError → 503 se modelo não carregado
    │
    ├── store.get_team_outcome(match_id)
    │   → KeyError → 404 se match_id não encontrado
    │
    ├── _build_input(row, numeric_feats, feature_names)
    │       ├── monta dict com colunas numéricas da row
    │       ├── adiciona competition_type como string
    │       ├── pd.get_dummies(df, columns=["competition_type"])
    │       │   → cria competition_type_Continental / Domestic League / World Cup
    │       ├── df.reindex(columns=feature_names, fill_value=0)
    │       │   → garante ordem e presença de todas as colunas do modelo
    │       └── .values.astype(np.float32)  → shape (1, n_features)
    │
    ├── session.run(None, {"float_input": X})
    │   → [labels_array, zipmap_probs]  (classificador)
    │
    ├── _extract_classifier_probs(outputs)
    │   → [p_home, p_draw, p_away]
    │
    └── monta dict resultado:
            home_win_probability = p_home
            draw_probability     = p_draw
            away_win_probability = p_away
            favorite_outcome     = labels[argmax(probs)]
            confidence_score     = max(probs)
            model_version        = registry.manifest_version
            generated_at         = datetime.now(UTC)
    │
    ▼
[predictions.py — router]
    │
    └── MatchOutcomeResponse(**result)
            │
            └── @model_validator: |sum - 1.0| < 0.001
                → 422 se probabilidades não somam 1
    │
    ▼
JSON Response 200
{
  "home_win_probability": 0.55,
  "draw_probability": 0.25,
  "away_win_probability": 0.20,
  "favorite_outcome": "HOME",
  "confidence_score": 0.55,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T00:00:00Z"
}
```

---

### 4.3 Endpoints em Detalhe

#### GET /health
```json
{
  "status": "ok",
  "model_version": "1.0.0",
  "models_loaded": ["match_outcome", "total_goals", "corners", "yellow_cards", "red_cards"],
  "store_ready": true
}
```

#### POST /v1/predict/match-outcome

**Input:** `team_outcome` parquet
**Modelo:** `match_outcome.onnx` (XGBoostClassifier)
**Output ONNX:** `[int_labels, list[dict{0:p, 1:p, 2:p}]]` (ZipMap)

Derivações:
```python
probs          = [p_home, p_draw, p_away]   # soma = 1.0
favorite_idx   = argmax(probs)              # 0=HOME, 1=DRAW, 2=AWAY
confidence     = max(probs)
```

#### POST /v1/predict/total-goals

**Input:** `team_sog` parquet
**Modelo:** `total_goals.onnx` (GBR)
**Output ONNX:** `[float_array]` → `expected_goals`

Derivações via Poisson:
```python
# P(gols > 2.5) = 1 - P(gols <= 2) = 1 - Poisson.cdf(2, lambda=expected)
over_25  = 1 - poisson.cdf(2, expected_goals)
under_25 = 1 - over_25

most_likely_range:
  expected < 1.5  → "0-1"
  expected < 3.5  → "2-3"
  expected >= 3.5 → "4+"

confidence = max(over_25, under_25)
```

#### POST /v1/predict/corners

**Input:** `team_outcome` parquet
**Modelo:** `corners.onnx` (GBR ou Poisson — melhor MAE em CV)
**Output ONNX:** `[float_array]` → `expected_corners`

Derivações:
```python
over_9  = 1 - poisson.cdf(9, expected_corners)
under_9 = 1 - over_9
```

#### POST /v1/predict/cards

**Dois modelos em sequência:**
- `yellow_cards.onnx` → `expected_yellow_cards`
- `red_cards.onnx`    → `expected_red_cards`

Ambos usam as mesmas features de `team_outcome`. Duas sessões ONNX são executadas para o mesmo `match_id`.

Derivações:
```python
over_3_yellow  = 1 - poisson.cdf(3, expected_yellow)
under_3_yellow = 1 - over_3_yellow
```

---

### 4.4 Tratamento de Erros

| Cenário | Exceção interna | HTTP | Body |
|---|---|---|---|
| `match_id` não numérico | `ValueError` na conversão | 400 | `"match_id deve ser numérico"` |
| `match_id` não encontrado | `KeyError` no feature_store | 404 | `"match_id=X não encontrado no dataset"` |
| Campo obrigatório ausente | Pydantic `ValidationError` | 422 | detail Pydantic padrão |
| Probabilidades fora de [0,1] | `ValueError` no response validator | 422 | `"Soma = X, esperado 1.0"` |
| Modelo ONNX não carregado | `RuntimeError` no inference | 503 | `"Modelo X não carregado"` |

---

## 5. Contrato com o Melchior

O Melchior (Java/Spring Boot) consome a API via `DelfosHttpClient` (WebClient):

```
Melchior                          Delfos
POST /v1/predict/match-outcome ──► router → inference → ONNX
{"match_id": "3788741"}        ◄── MatchOutcomeResponse JSON
{"season": "2022"}
```

**Ponto crítico — serialização do campo `match_id`:**

Jackson (Java) serializa por padrão como camelCase:
```json
{"matchId": "3788741"}   ← Java padrão
{"match_id": "3788741"}  ← Python espera
```

A Dupla 2 deve aplicar uma das soluções abaixo em `DelfosRequest.java`:

```java
// Opção A — anotação por campo (recomendada)
public record DelfosRequest(
    @JsonProperty("match_id") String matchId,
    @JsonProperty("season")   String season
) {}

// Opção B — configuração global no application.yml
spring:
  jackson:
    property-naming-strategy: SNAKE_CASE
```

**Padrão de resiliência (US-4.5):**
```
request
  └── @Retry(3 tentativas, 500ms backoff)
        └── @CircuitBreaker(abre após 5 falhas em 10 chamadas)
              └── fallback: StubPredictionService (modelVersion="stub-v1.0")
```

---

## 6. Decisões Técnicas Relevantes

### Por que o scaler não está dentro do ONNX

O `StandardScaler` é aplicado no ETL (`preprocessor.py`) antes de salvar os parquets. Os modelos foram treinados com dados já normalizados. Incluir o scaler no ONNX exigiria reconstruir os parâmetros de normalização para o subconjunto de features de cada modelo — uma operação sujeita a erros silenciosos.

Como a API carrega features dos parquets (já normalizados), o scaler não é necessário em runtime. Na integração com BetsAPI (dados brutos ao vivo), o export deverá empacotar `Pipeline([('scaler', scaler_subset), ('model', model)])`.

### Por que pd.get_dummies e não LabelEncoder/OrdinalEncoder

Os modelos baseados em árvore (XGBoost, GBR) tratam cada coluna independentemente. `get_dummies` cria colunas binárias ortogonais — o modelo pode aprender "Copa do Mundo aumenta a imprevisibilidade" sem assumir ordinalidade entre as categorias.

### Por que holdout estratificado por competition_type

Sem estratificação, o split aleatório poderia concentrar todas as partidas de Copa do Mundo no treino, resultando em métricas infladas (a Copa tem padrões estatísticos distintos de ligas domésticas). A estratificação garante que o holdout seja representativo de todas as competições.

### Por que GBR vs Poisson para contagens

Eventos de contagem (escanteios, cartões) têm distribuição naturalmente não-gaussiana, com cauda longa e valor mínimo = 0. O `PoissonRegressor` modela diretamente essa distribuição e tende a performar melhor para eventos raros (cartões vermelhos, média < 0.3/partida). O GBR pode superar o Poisson em contagens com maior variância. A seleção automática pelo MAE garante o melhor modelo por contexto.

### Por que feature_names_in_ no manifest

Durante `pd.get_dummies`, a ordem das colunas é determinada pelos valores únicos de `competition_type` no conjunto de treino, em ordem alfabética. Na inferência, um único match pode ter apenas uma categoria — sem o reindex guiado por `feature_names`, as colunas ficariam fora de ordem e o modelo produziria resultados incorretos silenciosamente.
