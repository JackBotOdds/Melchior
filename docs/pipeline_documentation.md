# Delfos v1.0 — Documentação do Pipeline de ML

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura do Pipeline](#2-arquitetura-do-pipeline)
3. [Coleta de Dados — StatsBomb Open Data](#3-coleta-de-dados--statsbomb-open-data)
4. [Tratamento dos Dados — ETL](#4-tratamento-dos-dados--etl)
5. [Features Utilizadas por Modelo](#5-features-utilizadas-por-modelo)
6. [Treinamento dos Modelos](#6-treinamento-dos-modelos)
7. [Resultados do Treinamento](#7-resultados-do-treinamento)
8. [Gráficos Gerados e Suas Interpretações](#8-gráficos-gerados-e-suas-interpretações)
9. [Serialização para ONNX](#9-serialização-para-onnx)
10. [API de Inferência (US-4.4)](#10-api-de-inferência-us-44)
11. [Como Executar](#11-como-executar)
12. [Estrutura de Arquivos de Saída](#12-estrutura-de-arquivos-de-saída)

---

## 1. Visão Geral

O Delfos v1.0 é um pipeline de aprendizado de máquina para predição de métricas de partidas de futebol. O sistema consome os dados abertos do StatsBomb, processa eventos de partida e treina 7 modelos preditivos cobrindo resultados, gols, escanteios, cartões e desempenho individual de jogadores.

### Métricas preditas

| ID   | Métrica                              | Tipo            | Modelo              |
|------|--------------------------------------|-----------------|---------------------|
| 3.1  | Resultado da partida (HOME/DRAW/AWAY) | Classificação   | XGBoostClassifier   |
| 3.2  | Total de gols                         | Regressão       | GBR                 |
| 3.3  | Total de escanteios                   | Regressão       | GBR ou Poisson      |
| 3.4  | Distribuição de gols (fração do time da casa) | Regressão | GBR             |
| 3.5  | Total de cartões vermelhos            | Regressão       | GBR ou Poisson      |
| 3.6  | Total de cartões amarelos             | Regressão       | GBR ou Poisson      |
| —    | Chutes a gol por jogador (baseline)   | Regressão       | GBR                 |

---

## 2. Arquitetura do Pipeline

```
StatsBomb Open Data (JSON via HTTP)
            |
            v
   etl/statsbomb_loader.py
   [JSON -> CSV por competição]
            |
            v
   etl/data_loader.py
   [glob dinâmico -> DataFrames]
            |
            v
   etl/cleaner.py
   [remoção de colunas constantes + imputação]
            |
            v
   etl/feature_engineer.py
   [features de interação + anti-leakage]
            |
            v
   etl/preprocessor.py
   [split 90/10 + StandardScaler + Parquet]
            |
            +---> data/processed/*_train.parquet  (90%)
            |
            +---> data/processed/*_holdout.parquet (10%)
                        |
                        v
           delfos/training/train_*.py
           [GridSearchCV + CV k=5 + MLflow]
                        |
                        +---> models/trained/*.joblib
                        |
                        +---> reports/plots/*.png
                        |
                        v
           delfos/serialization/export_models.py
           [sklearn -> ONNX + manifest]
                        |
                        +---> models/onnx/*.onnx
                        +---> models/onnx/model_manifest.json
```

---

## 3. Coleta de Dados — StatsBomb Open Data

### Fonte

Os dados são obtidos do **StatsBomb Open Data** via pacote Python `statsbombpy`. O dataset aberto contém eventos detalhados de aproximadamente **75 competições** (~5.000+ partidas) incluindo:

- Copa do Mundo FIFA (masculina)
- Ligas domésticas europeias (Premier League, La Liga, Ligue 1, Serie A, Bundesliga, etc.)
- Competições continentais (Champions League, Copa América, etc.)
- Ligas das Américas (MLS, Liga Profesional, etc.)

### Processo de extração (`etl/statsbomb_loader.py`)

Para cada competição/temporada disponível:

1. `sb.competitions()` — lista todas as competições disponíveis
2. `sb.matches(competition_id, season_id)` — lista partidas de cada competição
3. `sb.events(match_id)` — carrega todos os eventos de cada partida (passes, chutes, faltas, cartões)

### Granularidades geradas

Cada competição gera **3 arquivos CSV** em `data/raw/`:

| Arquivo                         | Descrição                              | Granularidade       |
|--------------------------------|----------------------------------------|---------------------|
| `{ctx}_team_outcome.csv`       | Resultado, placar, estatísticas de 1T  | 1 linha por partida |
| `{ctx}_team_sog.csv`           | Chutes, gols, distribuição             | 1 linha por partida |
| `{ctx}_player_sog.csv`         | Chutes a gol por jogador               | 1 linha por jogador por partida |

O `{ctx}` (context) é derivado do nome da competição, ex: `comp43_s106_fifa_world_cup_2022`.

### Campos extraídos de eventos

A partir dos eventos brutos de cada partida, o loader calcula:

**Para `team_outcome`:**
- `ht_goals_home/away`, `ht_goals_diff` — gols de 1T
- `ht_shots_home/away`, `ht_shots_diff` — chutes de 1T
- `ht_sog_home/away`, `ht_sog_diff` — chutes a gol de 1T
- `ht_fouls_home/away`, `ht_fouls_diff` — faltas de 1T
- `ht_corners_home/away` — escanteios de 1T
- `ht_yellow_cards_home/away` — cartões amarelos de 1T
- `total_goals`, `total_corners`, `total_yellow_cards`, `total_red_cards`
- `outcome` — alvo: 0=HOME, 1=DRAW, 2=AWAY

**Para `team_sog`:**
- Subset das features acima + `goals_home_frac` (fração de gols do time da casa)

**Para `player_sog`:**
- `total_sog` — total de chutes a gol do jogador na partida
- `ht_passes`, `ht_touches`, `ht_dribbles` — atividade de 1T do jogador

### Classificação de competição

Cada competição recebe um `competition_type` no momento da extração:

| Valor             | Critério                                                    |
|-------------------|-------------------------------------------------------------|
| `"World Cup"`     | Nome contém "world cup" (excluindo feminino e sub-20)      |
| `"Domestic League"` | Nome contém "league", "liga", "ligue", "bundesliga", etc. |
| `"Continental"`   | Demais competições (Champions League, Copa América, etc.)   |

### Incremental por padrão

O loader verifica se os 3 CSVs de uma competição já existem antes de re-processar. Use `--force` para regenerar tudo.

---

## 4. Tratamento dos Dados — ETL

### 4.1. Carregamento (`etl/data_loader.py`)

Usa `glob` dinâmico para descobrir todos os arquivos `*_{granularidade}.csv` em `data/raw/`. Concatena todos os arquivos de uma mesma granularidade em um único DataFrame, preservando a coluna `source_context` (nome do arquivo de origem) para rastreabilidade.

### 4.2. Limpeza (`etl/cleaner.py`)

| Regra | Ação |
|-------|------|
| `ht_corners_diff` em `team_outcome` | Removida — coluna constante (std=0) identificada na EDA |
| Valores nulos em colunas numéricas | Imputados pela **mediana** da coluna |

A remoção de `ht_corners_diff` é uma proteção contra multicolinearidade: a diferença de escanteios no 1T possui variância zero em muitos jogos, não adicionando informação preditiva.

### 4.3. Engenharia de Features (`etl/feature_engineer.py`)

#### Feature `competition_type`

Mapeada de `source_context` apenas quando não veio preenchida pelo `statsbomb_loader`:

```
source_context "wc2022"          -> "World Cup"
source_context "ligue1_2021_2022" -> "Ligue 1"
(demais)                          -> "Other"
```

Quando os dados vêm do `statsbomb_loader` moderno, `competition_type` já está preenchida diretamente (World Cup / Domestic League / Continental).

#### Feature de interação para `player_sog`

Detectada via `source_context` (robustez a qualquer valor de `competition_type`):

| Feature                  | Lógica                                                       |
|--------------------------|--------------------------------------------------------------|
| `player_id_x_world_cup`  | = `player_id` se `source_context` contém "wc/world_cup/comp43", senão 0 |

Permite ao modelo aprender comportamentos específicos de jogadores no contexto da Copa do Mundo.

### 4.4. Pré-processamento e Split (`etl/preprocessor.py`)

#### Split treino/holdout

```
Total de dados  ->  90% treino  +  10% holdout
```

- Estratificado por `competition_type` para garantir proporção representativa das competições em ambos os conjuntos
- Semente fixa: `random_state=42`
- O holdout **não é usado durante o treinamento** — apenas para avaliação final

#### Normalização (StandardScaler)

O scaler é **fitado apenas no conjunto de treino** e aplicado ao holdout com `transform()`, prevenindo data leakage de estatísticas do holdout para o treino.

**Colunas NÃO escalonadas** (targets e identificadores):

```
outcome, total_goals, goals_home_frac, total_corners,
total_red_cards, total_yellow_cards, total_sog,
home_score, away_score, match_id, player_id
```

A exclusão dos targets evita que o modelo de classificação receba classes flutuantes (ex: 0.0 → -0.95, 1.0 → 0.23, 2.0 → 1.43) em vez de inteiros [0, 1, 2].

#### Saídas geradas

- `data/processed/{gran}_train.parquet` — 90% para treino
- `data/processed/{gran}_holdout.parquet` — 10% para avaliação
- `models/preprocessors/scaler_{gran}.pkl` — scaler serializado

---

## 5. Features Utilizadas por Modelo

### 5.1. Match Outcome (Resultado — Métrica 3.1)

**Granularidade:** `team_outcome` | **Alvo:** `outcome` (0=HOME, 1=DRAW, 2=AWAY)

| Feature            | Descrição                                    | Tipo     |
|--------------------|----------------------------------------------|----------|
| `ht_goals_diff`    | Diferença de gols no 1T (home - away)        | Numérica |
| `ht_shots_diff`    | Diferença de chutes no 1T                    | Numérica |
| `ht_sog_diff`      | Diferença de chutes a gol no 1T              | Numérica |
| `ht_fouls_diff`    | Diferença de faltas no 1T                    | Numérica |
| `competition_type` | Tipo de competição (one-hot encoded)          | Categórica |

> `ht_corners_diff` foi excluído por ter desvio padrão = 0 (CA-US-4.2.3).

### 5.2. Total Goals (Gols Totais — Métrica 3.2) e Goals Distribution (Métrica 3.4)

**Granularidade:** `team_sog` | **Alvos:** `total_goals`, `goals_home_frac`

| Feature            | Descrição                            | Tipo     |
|--------------------|--------------------------------------|----------|
| `ht_shots_home`    | Chutes do time da casa no 1T         | Numérica |
| `ht_shots_away`    | Chutes do time visitante no 1T       | Numérica |
| `ht_sog_home`      | Chutes a gol do time da casa no 1T   | Numérica |
| `ht_sog_away`      | Chutes a gol do time visitante no 1T | Numérica |
| `ht_goals_home`    | Gols do time da casa no 1T           | Numérica |
| `ht_goals_away`    | Gols do time visitante no 1T         | Numérica |
| `competition_type` | Tipo de competição (one-hot encoded)  | Categórica |

### 5.3. Corners (Escanteios — Métrica 3.3)

**Granularidade:** `team_outcome` | **Alvo:** `total_corners`

| Feature              | Descrição                              | Tipo     |
|----------------------|----------------------------------------|----------|
| `ht_shots_home`      | Chutes do time da casa no 1T           | Numérica |
| `ht_shots_away`      | Chutes do time visitante no 1T         | Numérica |
| `ht_fouls_home`      | Faltas do time da casa no 1T           | Numérica |
| `ht_fouls_away`      | Faltas do time visitante no 1T         | Numérica |
| `ht_corners_home`    | Escanteios do time da casa no 1T       | Numérica |
| `ht_corners_away`    | Escanteios do time visitante no 1T     | Numérica |
| `competition_type`   | Tipo de competição (one-hot encoded)    | Categórica |

### 5.4. Cards (Cartões — Métricas 3.5 e 3.6)

**Granularidade:** `team_outcome` | **Alvos:** `total_red_cards`, `total_yellow_cards`

| Feature                  | Descrição                                   | Tipo     |
|--------------------------|---------------------------------------------|----------|
| `ht_fouls_home`          | Faltas do time da casa no 1T                | Numérica |
| `ht_fouls_away`          | Faltas do time visitante no 1T              | Numérica |
| `ht_yellow_cards_home`   | Cartões amarelos do time da casa no 1T      | Numérica |
| `ht_yellow_cards_away`   | Cartões amarelos do time visitante no 1T    | Numérica |
| `competition_type`       | Tipo de competição (one-hot encoded)         | Categórica |

### 5.5. Player SOG (Chutes a Gol por Jogador — Baseline EDA)

**Granularidade:** `player_sog` | **Alvo:** `total_sog`

| Feature                  | Descrição                                           | Tipo     |
|--------------------------|-----------------------------------------------------|----------|
| `ht_passes`              | Passes do jogador no 1T                             | Numérica |
| `ht_touches`             | Toques (carries) do jogador no 1T                   | Numérica |
| `ht_dribbles`            | Dribles completos do jogador no 1T                  | Numérica |
| `player_id_x_world_cup`  | ID do jogador x Copa do Mundo (interação)           | Numérica |
| `competition_type`       | Tipo de competição (one-hot encoded)                 | Categórica |

---

## 6. Treinamento dos Modelos

### Configuração geral

| Parâmetro          | Valor                                      |
|--------------------|--------------------------------------------|
| Cross-validation   | k=5 (StratifiedKFold implícito no sklearn) |
| Random state       | 42                                         |
| Paralelismo        | `n_jobs=-1` (todos os núcleos)             |
| MLflow backend     | SQLite local (`mlflow.db`)                 |
| Otimização         | `GridSearchCV` com `cv=5`                  |

### Modelos e hiperparâmetros pesquisados

#### Match Outcome — XGBoostClassifier

```python
PARAM_GRID = {
    "n_estimators": [100, 200],
    "max_depth":    [3, 5],
}
# Parâmetros fixos: learning_rate=0.05, eval_metric="mlogloss"
```

Métrica de seleção: `accuracy`

#### Total Goals, Goals Distribution, Corners — GradientBoostingRegressor

```python
PARAM_GRID = {
    "n_estimators":  [100, 200],
    "max_depth":     [3, 5],
    "learning_rate": [0.05, 0.1],
}
```

Métrica de seleção: `neg_mean_absolute_error`

#### Corners, Red Cards, Yellow Cards — GBR vs PoissonRegressor

Ambos são treinados e avaliados por MAE em CV k=5. O modelo com menor MAE é selecionado automaticamente:

```
Se MAE(GBR) <= MAE(Poisson)  ->  GBR selecionado
Caso contrário                ->  PoissonRegressor selecionado
```

O `PoissonRegressor` é especialmente adequado para contagens de eventos raros (cartões vermelhos têm média < 0.3/partida).

#### Player SOG — GradientBoostingRegressor

```python
PARAM_GRID = {
    "n_estimators":  [100, 200],
    "max_depth":     [3, 5],
    "learning_rate": [0.05, 0.1],
}
```

Métrica de seleção: `r2`

### Fluxo de treinamento (`common.cv_and_log`)

Para cada modelo:

1. `GridSearchCV.fit()` — encontra melhores hiperparâmetros
2. `cross_val_score(cv=5)` — avalia o melhor estimador com CV
3. `mlflow.log_params()` + `mlflow.log_metric()` — registra métricas
4. `model.fit(X, y)` — treina o modelo final no conjunto completo de treino
5. `mlflow.sklearn.log_model()` — serializa o modelo no MLflow
6. `mlflow.register_model()` — registra no Model Registry
7. `joblib.dump()` — salva em `models/trained/{nome}.joblib`

### Nomeação dos experimentos MLflow

| Experimento         | Script                  |
|---------------------|-------------------------|
| `match-outcome`     | `train_match_outcome.py` |
| `total-goals`       | `train_total_goals.py`   |
| `goals-distribution`| `train_total_goals.py`   |
| `corners`           | `train_corners.py`       |
| `red-cards`         | `train_cards.py`         |
| `yellow-cards`      | `train_cards.py`         |
| `player-sog`        | `train_player_sog.py`    |

---

## 7. Resultados do Treinamento

Após o treino, cada modelo é avaliado no **holdout (10%)** — dados que nunca participaram do treinamento ou da seleção de hiperparâmetros.

### Saída CLI ao final de cada modelo

**Classificador (match-outcome):**
```
================================================================
  AVALIAÇÃO — match-outcome  |  Holdout 10%  |  Classificador
================================================================
  Accuracy      : X.XXXX
  Amostras      : NNNN

  [classification_report com precision/recall/f1 por classe]

  Features utilizadas (top-10 por importância):
     1. ht_goals_diff                        X.XXXX
     2. ht_sog_diff                          X.XXXX
     ...
```

**Regressores (demais modelos):**
```
================================================================
  AVALIAÇÃO — total-goals  |  Holdout 10%  |  Regressor
================================================================
  MAE           : X.XXXX
  RMSE          : X.XXXX
  R²            : X.XXXX
  Amostras      : NNNN

  Features utilizadas (top-10 por importância):
     1. ht_goals_home                        X.XXXX
     ...
```

### Baselines de referência (CA-US-4.2.1)

| Modelo       | Métrica | Baseline mínimo |
|--------------|---------|-----------------|
| `player-sog` | R²      | >= 0.26         |
| `player-sog` | MAE     | <= 0.24         |

O pipeline exibe automaticamente se o critério de aceite foi atingido:
```
[OK] CA-US-4.2.1 APROVADO — modelo >= baseline EDA.
```
ou:
```
[AVISO] CA-US-4.2.1 — abaixo do baseline. R²=X.XXX MAE=X.XXX
```

### Referências de desempenho esperado

Com ~5.000 partidas e dados de todas as competições StatsBomb, os valores típicos são:

| Modelo              | Métrica esperada | Intervalo típico |
|---------------------|------------------|------------------|
| match-outcome       | Accuracy         | 0.45 – 0.60      |
| total-goals         | MAE              | 0.8 – 1.4 gols   |
| corners             | MAE              | 2.0 – 4.0        |
| red-cards           | MAE              | 0.2 – 0.5        |
| yellow-cards        | MAE              | 0.8 – 1.5        |
| player-sog          | R²               | 0.20 – 0.35      |

> Nota: resultados de partidas de futebol têm alta aleatoriedade intrínseca. Um accuracy de 50% para previsão de resultado triplo (HOME/DRAW/AWAY) já supera o baseline aleatório de 33%.

---

## 8. Gráficos Gerados e Suas Interpretações

Todos os gráficos são salvos em `reports/plots/` ao final de cada script de treinamento.

### 8.1. Matriz de Confusão (`{modelo}_confusion_matrix.png`)

**Gerado por:** `evaluate_classifier` — apenas para `match-outcome`

**O que mostra:** Uma grade 3x3 onde cada célula [i, j] indica quantas vezes o modelo predisse a classe j quando a classe real era i.

```
           Predito
           HOME  DRAW  AWAY
Real HOME [  x    x    x  ]
     DRAW [  x    x    x  ]
     AWAY [  x    x    x  ]
```

**Como interpretar:**
- Diagonal principal (top-left a bottom-right): predições corretas
- Células fora da diagonal: erros de classificação
- Um modelo que confunde muito DRAW com HOME/AWAY é esperado — empates são os mais difíceis de prever
- Células escuras na diagonal indicam bom desempenho na classe correspondente

### 8.2. Real vs Predito — Scatter e Resíduos (`{modelo}_actual_vs_predicted.png`)

**Gerado por:** `evaluate_regressor` — para todos os modelos de regressão

O arquivo contém **dois subgráficos lado a lado**:

#### Subgráfico esquerdo: Scatter Real vs Predito

**O que mostra:** Cada ponto é uma partida/jogador do holdout. O eixo X é o valor real e o eixo Y é o valor predito pelo modelo. A linha vermelha tracejada representa a predição perfeita (real = predito).

**Como interpretar:**
- Pontos próximos à linha vermelha = boas predições
- Dispersão vertical larga = alta variância do erro
- Viés sistemático (nuvem deslocada acima/abaixo) = o modelo está super ou subestimando
- Para `total_goals`: espera-se concentração em valores inteiros baixos (0-4)

#### Subgráfico direito: Distribuição de Resíduos

**O que mostra:** Histograma de `(real - predito)` para todas as amostras do holdout.

**Como interpretar:**
- Distribuição centrada em 0 = modelo sem viés sistemático
- Distribuição simétrica = erros distribuídos igualmente para cima e para baixo
- Distribuição assimétrica (cauda longa) = o modelo erra mais em um sentido
- Para `total_red_cards`: espera-se grande pico em 0 (maioria das partidas sem cartão vermelho)

### 8.3. Importância de Features (`{modelo}_feature_importance.png`)

**Gerado por:** todos os modelos (classificação e regressão)

**O que mostra:** Gráfico de barras horizontais com as top-15 features mais importantes segundo o modelo, em ordem decrescente de importância.

**Como interpretar:**
- Importância alta: a feature contribui significativamente para as predições do modelo
- Importância baixa/zero: a feature tem pouco poder preditivo (candidata a remoção em versões futuras)
- Para `match-outcome`: espera-se que `ht_goals_diff` seja a feature dominante
- Para `player-sog`: espera-se que `avg_total_sog_ligue1` seja a feature dominante (~40%), validando que o histórico individual do jogador é o melhor preditor

**Valores de importância para GBR:** baseados em ganho médio de impureza (Gini/MSE) por split. Somam ~1.0.

**Valores de importância para Poisson:** coeficientes absolutos, não somam 1.0.

### Todos os arquivos gerados por modelo

| Modelo              | Arquivos gerados                                                                       |
|---------------------|----------------------------------------------------------------------------------------|
| `match-outcome`     | `match-outcome_confusion_matrix.png`, `match-outcome_feature_importance.png`          |
| `total-goals`       | `total-goals_actual_vs_predicted.png`, `total-goals_feature_importance.png`           |
| `goals-distribution`| `goals-distribution_actual_vs_predicted.png`, `goals-distribution_feature_importance.png` |
| `corners`           | `corners_actual_vs_predicted.png`, `corners_feature_importance.png`                  |
| `red-cards`         | `red-cards_actual_vs_predicted.png`, `red-cards_feature_importance.png`              |
| `yellow-cards`      | `yellow-cards_actual_vs_predicted.png`, `yellow-cards_feature_importance.png`        |
| `player-sog`        | `player-sog_actual_vs_predicted.png`, `player-sog_feature_importance.png`            |

---

## 9. Serialização para ONNX

O módulo `delfos/serialization/export_models.py` converte os modelos treinados do formato sklearn (`.joblib`) para o formato **ONNX** (Open Neural Network Exchange), que pode ser consumido por APIs e sistemas de inferência em produção.

### Processo

1. Carrega cada modelo do MLflow Model Registry (stage `None` = mais recente)
2. Infere o número de features de `model.n_features_in_` (dinâmico, respeita one-hot encoding)
3. Converte via `skl2onnx.convert_sklearn()` com `opset=17`
4. Salva em `models/onnx/{nome}_v1.0.0.onnx`
5. Gera `models/onnx/model_manifest.json`

### Model Manifest

```json
{
  "version": "1.0.0",
  "generated_at": "2024-...",
  "models": [
    {
      "name": "match_outcome",
      "registry_name": "match-outcome",
      "version": "1.0.0",
      "onnx_path": "models/onnx/match_outcome_v1.0.0.onnx",
      "n_features": 7,
      "mlflow_run_id": "...",
      "metrics": {"accuracy_mean": 0.52, ...}
    },
    ...
  ]
}
```

O manifest serve como contrato para a API (US-4.4), informando o número de features esperadas e as métricas de cada modelo.

---

## 10. API de Inferência (US-4.4)

### Estrutura

```
delfos/api/
├── app.py                        ← FastAPI + CORS + lifespan (eager loading)
├── routers/
│   ├── health.py                 ← GET /health
│   └── predictions.py           ← POST /v1/predict/*
├── schemas/
│   ├── request.py                ← PredictionRequest (match_id, season)
│   └── response.py               ← MatchOutcomeResponse, TotalGoalsResponse, etc.
└── services/
    ├── model_registry.py         ← carrega ONNX + manifest na inicialização
    ├── feature_store.py          ← lookup match_id → features nos parquets
    └── inference.py              ← executa ONNX e formata resposta
```

### Endpoints

| Método | Rota | Resposta | CA |
|--------|------|----------|----|
| GET | `/health` | `{status, model_version, models_loaded, store_ready}` | 4.4.1 |
| POST | `/v1/predict/match-outcome` | probabilidades HOME/DRAW/AWAY | 4.4.2 |
| POST | `/v1/predict/total-goals` | expected_goals + over/under 2.5 | 4.4.3 |
| POST | `/v1/predict/corners` | expected_corners + over/under 9 | 4.4.4 |
| POST | `/v1/predict/cards` | yellow + red cards + over/under 3 amarelos | 4.4.5 |

### Request

Todos os endpoints aceitam:
```json
{ "match_id": "3788741", "season": "2022" }
```

`match_id` deve ser o ID numérico StatsBomb (inteiro como string). `season` é aceito mas não utilizado no lookup (Sprint 1 — IDs StatsBomb são globalmente únicos).

### Fluxo de inferência por endpoint

```
match_id (string)
    │
    ▼
feature_store.get_team_outcome(match_id) ou get_team_sog(match_id)
    │ → row com features já normalizadas (StandardScaler aplicado no ETL)
    │ → competition_type como string ("World Cup", "Domestic League", "Continental")
    ▼
inference._build_input()
    │ → pd.get_dummies(competition_type) → colunas binárias
    │ → reindex com feature_names do modelo (ordem do treino)
    │ → converte para float32 numpy array
    ▼
onnxruntime.InferenceSession.run()
    │ → match_outcome: [labels, ZipMap({0: p_home, 1: p_draw, 2: p_away})]
    │ → regressores:   [float array]
    ▼
Derivações na resposta:
    │ → over/under: scipy.stats.poisson.cdf(threshold, lambda=expected)
    │ → most_likely_range: "0-1" | "2-3" | "4+" baseado em expected_goals
    │ → confidence_score: max(probs) para classificador, max(over,under) para regressores
    ▼
Response Pydantic validado e retornado
```

### Tratamento de erros

| Cenário | HTTP |
|---------|------|
| `match_id` não numérico | 400 |
| `match_id` não encontrado nos parquets | 404 |
| Campo obrigatório ausente no body | 422 |
| Modelo ONNX não carregado | 503 |

### Nota sobre o scaler nos arquivos ONNX

O `StandardScaler` é aplicado no ETL (`preprocessor.py`) antes de salvar os parquets. Os modelos foram treinados com dados já normalizados e os arquivos ONNX esperam entrada pré-normalizada. Como o `feature_store` carrega features diretamente dos parquets normalizados, nenhuma transformação adicional é necessária em runtime.

Na integração com a BetsAPI (sprint futura com dados ao vivo), o scaler deverá ser incluído no pipeline ONNX via `sklearn.pipeline.Pipeline([('scaler', scaler), ('model', model)])`, permitindo que a API receba features brutas.

### Contrato com o Melchior (US-4.5)

O Melchior (Java/Spring Boot) consome esta API via `DelfosHttpClient`. Ponto de atenção no contrato:

> **Jackson serializa `matchId` como camelCase por padrão.** O Python espera `match_id` (snake_case). A Dupla 2 deve anotar o campo Java com `@JsonProperty("match_id")` ou configurar `spring.jackson.property-naming-strategy=SNAKE_CASE` no `application.yml`.

---

## 11. Como Executar

### Requisitos

- Python 3.11+
- Dependências em `requirements-ml.txt`

### Execução completa (download + ETL + treino)

```bash
bash run_pipeline.sh
```

> Tempo estimado: 30–90 minutos (depende da velocidade de rede para download dos dados StatsBomb)

### Pular download (dados já baixados)

```bash
bash run_pipeline.sh --skip-etl
```

### Forçar re-download de todos os CSVs

```bash
bash run_pipeline.sh --force
```

### Execução etapa por etapa

```bash
# 1. Download JSON -> CSV (todas as competições)
python -m etl.statsbomb_loader

# 2. ETL: CSV -> Parquet + split + scaler
python -c "
from pathlib import Path
from etl.data_loader import load_all
from etl.cleaner import clean
from etl.feature_engineer import engineer
from etl.preprocessor import fit_and_split
dfs = load_all(Path('data/raw'))
dfs = clean(dfs)
dfs = engineer(dfs)
fit_and_split(dfs, Path('models/preprocessors'), Path('data/processed'))
"

# 3. Treinamento
python run_pipeline.py --skip-etl

# 4. Exportar para ONNX (após treinamento)
python -m delfos.serialization.export_models

# 5. Visualizar experimentos MLflow
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

### Iniciar a API de inferência

```bash
# Após o treinamento e exportação ONNX:
uvicorn delfos.api.app:app --reload --port 8000

# Verificar:
curl http://localhost:8000/health

# Testar predição:
curl -X POST http://localhost:8000/v1/predict/match-outcome \
  -H "Content-Type: application/json" \
  -d '{"match_id": "3788741", "season": "2022"}'

# Swagger UI:
# http://localhost:8000/docs
```

### Executar apenas os testes

```bash
pytest tests/test_etl.py tests/test_api.py -v
```

---

## 12. Estrutura de Arquivos de Saída

```
Melchior/
├── data/
│   ├── raw/
│   │   ├── comp43_s106_fifa_world_cup_2022_team_outcome.csv
│   │   ├── comp43_s106_fifa_world_cup_2022_team_sog.csv
│   │   ├── comp43_s106_fifa_world_cup_2022_player_sog.csv
│   │   └── ... (3 arquivos x ~75 competições)
│   └── processed/
│       ├── team_outcome_train.parquet
│       ├── team_outcome_holdout.parquet
│       ├── team_sog_train.parquet
│       ├── team_sog_holdout.parquet
│       ├── player_sog_train.parquet
│       └── player_sog_holdout.parquet
│
├── models/
│   ├── preprocessors/
│   │   ├── scaler_team_outcome.pkl
│   │   ├── scaler_team_sog.pkl
│   │   └── scaler_player_sog.pkl
│   ├── trained/
│   │   ├── match-outcome.joblib
│   │   ├── total-goals.joblib
│   │   ├── goals-distribution.joblib
│   │   ├── corners.joblib
│   │   ├── red-cards.joblib
│   │   ├── yellow-cards.joblib
│   │   └── player-sog.joblib
│   └── onnx/
│       ├── match_outcome_v1.0.0.onnx
│       ├── total_goals_v1.0.0.onnx
│       ├── goals_distribution_v1.0.0.onnx
│       ├── corners_v1.0.0.onnx
│       ├── red_cards_v1.0.0.onnx
│       ├── yellow_cards_v1.0.0.onnx
│       ├── player_sog_v1.0.0.onnx
│       └── model_manifest.json
│
├── reports/
│   └── plots/
│       ├── match-outcome_confusion_matrix.png
│       ├── match-outcome_feature_importance.png
│       ├── total-goals_actual_vs_predicted.png
│       ├── total-goals_feature_importance.png
│       ├── goals-distribution_actual_vs_predicted.png
│       ├── goals-distribution_feature_importance.png
│       ├── corners_actual_vs_predicted.png
│       ├── corners_feature_importance.png
│       ├── red-cards_actual_vs_predicted.png
│       ├── red-cards_feature_importance.png
│       ├── yellow-cards_actual_vs_predicted.png
│       ├── yellow-cards_feature_importance.png
│       ├── player-sog_actual_vs_predicted.png
│       └── player-sog_feature_importance.png
│
└── mlflow.db  (histórico de experimentos — abrir com mlflow ui)
```
