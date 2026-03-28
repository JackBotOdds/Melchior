# Delfos v1.0 — Pipeline ETL e Treinamento

## Visão geral

```
StatsBomb Open Data (JSON)
         │
         ▼  etl/statsbomb_loader.py
data/raw/*.csv
         │
         ▼  etl/data_loader.py
         │  etl/cleaner.py
         │  etl/feature_engineer.py
         │  etl/preprocessor.py
         │
         ├── data/processed/team_outcome_{train,holdout}.parquet
         ├── data/processed/team_sog_{train,holdout}.parquet
         ├── data/processed/player_sog_{train,holdout}.parquet
         └── models/preprocessors/scaler_{gran}.pkl
                  │
                  ▼  delfos/training/train_*.py
                  │  (MLflow tracking → mlflow.db)
                  │
                  ▼  delfos/serialization/export_models.py
                  │
                  ├── models/onnx/*.onnx
                  └── models/onnx/model_manifest.json
```

Para executar o pipeline completo:
```bash
python run_pipeline.py                   # ETL + treinamento
python run_pipeline.py --skip-etl        # só treinamento (dados já existem)
python -m delfos.serialization.export_models   # exporta para ONNX
```

---

## Etapa 1 — Extração StatsBomb (`etl/statsbomb_loader.py`)

**Fonte:** StatsBomb Open Data (~3.500 partidas, 75+ competições).

**O que extrai:**
- Eventos de chute (`type.name == "Shot"`) filtrados por `period == 1` → features `ht_*`
- Eventos de falta, escanteio, cartão — todos do 1º tempo
- Score no intervalo (`team_score_ht`) → `ht_goals_home/away`

**Granularidades geradas:**

| CSV | Chave | Features |
|---|---|---|
| `comp{id}_s{id}_team_outcome.csv` | `match_id` | `ht_goals_diff`, `ht_shots_diff`, `ht_sog_diff`, `ht_fouls_diff`, `ht_corners_*`, `ht_yellow_cards_*`, `outcome` |
| `comp{id}_s{id}_team_sog.csv` | `match_id` | `ht_shots_home/away`, `ht_sog_home/away`, `ht_goals_home/away`, `total_goals` |
| `comp{id}_s{id}_player_sog.csv` | `match_id + player_id` | `ht_passes`, `ht_touches`, `ht_dribbles`, `ht_sog` |

**Prevenção de data leakage:**
Apenas eventos do 1º tempo (`period == 1`) são usados como features. O alvo (`outcome`, `total_goals`, etc.) é calculado sobre o jogo completo.

---

## Etapa 2 — ETL (`etl/`)

### data_loader.py
Lê todos os CSVs de `data/raw/` e organiza em dicionários por granularidade.

### cleaner.py
- Remove linhas com `match_id` nulo
- Converte tipos numéricos
- Remove duplicatas por `match_id` (ou `match_id + player_id` para player_sog)

### feature_engineer.py
- Deriva `competition_type` a partir do nome do arquivo fonte (mapeamento hardcoded):
  ```
  arquivos com "wc2022"           → "World Cup"
  arquivos com "champions_league" → "Continental"
  demais                          → "Domestic League"
  ```
- Para `player_sog`: cria feature de interação `player_id_x_world_cup` (binária)

### preprocessor.py (`fit_and_split`)
1. Split **90% treino / 10% holdout** estratificado por `competition_type`
2. `StandardScaler` fit **apenas no conjunto de treino**
3. Transforma treino e holdout com o mesmo scaler
4. Salva parquets em `data/processed/{gran}_{split}.parquet`
5. Salva scalers em `models/preprocessors/scaler_{gran}.pkl`

Colunas excluídas da normalização: `match_id`, `player_id`, `competition_type`, colunas de alvo (`outcome`, `total_goals`, etc.).

---

## Etapa 3 — Treinamento (`delfos/training/`)

Todos os scripts seguem o mesmo padrão:
1. Carrega os parquets de treino
2. Aplica `pd.get_dummies` no `competition_type`
3. GridSearchCV com 5-fold CV
4. Avalia no holdout
5. Registra no MLflow e no Model Registry

### `train_match_outcome.py` — Resultado (HOME/DRAW/AWAY)

| Parâmetro | Valor |
|---|---|
| Dataset | `team_outcome` |
| Features | `ht_goals_diff`, `ht_shots_diff`, `ht_sog_diff`, `ht_fouls_diff`, `competition_type` |
| Alvo | `outcome` (0=HOME, 1=DRAW, 2=AWAY) |
| Modelo | `XGBClassifier` |
| Grid | `n_estimators=[100,200]`, `max_depth=[3,5]` |
| Métrica | Accuracy |
| Exportação ONNX | Pendente (incompatibilidade XGBoost 3.x + onnxmltools) |

### `train_total_goals.py` — Total de gols

| Parâmetro | Valor |
|---|---|
| Dataset | `team_sog` |
| Features | `ht_shots_home/away`, `ht_sog_home/away`, `ht_goals_home/away`, `competition_type` |
| Alvo | `total_goals` |
| Modelo | `GradientBoostingRegressor` |
| Grid | `n_estimators=[100,200]`, `max_depth=[3,5]`, `learning_rate=[0.05,0.1]` |
| Métrica | MAE = 1.012 ± 0.034 |

Treina também o modelo `goals_distribution` (fração de gols da equipe da casa).

### `train_corners.py` — Total de escanteios

| Parâmetro | Valor |
|---|---|
| Dataset | `team_outcome` |
| Features | `ht_shots_home/away`, `ht_fouls_home/away`, `ht_corners_home/away`, `competition_type` |
| Alvo | `total_corners` |
| Modelos candidatos | `GradientBoostingRegressor` vs `PoissonRegressor` |
| Seleção | Menor MAE no holdout |
| Métrica | MAE = 1.945 ± 0.044 |

### `train_cards.py` — Cartões

| Parâmetro | Valor |
|---|---|
| Dataset | `team_outcome` |
| Features | `ht_fouls_home/away`, `ht_yellow_cards_home/away`, `competition_type` |
| Alvos | `total_yellow_cards` e `total_red_cards` (modelos separados) |
| Modelos candidatos | `GradientBoostingRegressor` vs `PoissonRegressor` |
| Seleção | Menor MAE por alvo |
| Métrica (yellow) | MAE = 1.403 ± 0.040 |
| Métrica (red) | MAE = 0.172 ± 0.007 |

Nota: cartões vermelhos têm frequência muito baixa (< 0.3 por jogo em média). O MAE baixo reflete que o modelo aprende a prever valores próximos de zero.

---

## Etapa 4 — Exportação ONNX (`delfos/serialization/export_models.py`)

Para cada modelo no `REGISTRY_TO_FILE`:
1. Carrega do MLflow Model Registry (stage=`None`, versão mais recente)
2. Converte para ONNX via `skl2onnx.convert_sklearn`
   - Para `XGBClassifier`: usa `onnxmltools` + conversão especial (booster.feature_names → None antes da conversão)
3. Salva em `models/onnx/{nome}_v1.0.0.onnx`
4. Gera `models/onnx/model_manifest.json` com métricas, feature_names e caminhos

**Manifest de exemplo:**
```json
{
  "version": "1.0.0",
  "generated_at": "2026-03-28T09:07:54Z",
  "models": [
    {
      "name": "total_goals",
      "registry_name": "total-goals",
      "version": "1.0.0",
      "onnx_path": "models/onnx/total_goals_v1.0.0.onnx",
      "n_features": 9,
      "feature_names": ["ht_shots_home", "ht_shots_away", "..."],
      "metrics": {"MAE": 1.012},
      "generated_at": "2026-03-28T09:07:54Z"
    }
  ],
  "errors": [
    {
      "name": "match-outcome",
      "error": "'split_condition'"
    }
  ]
}
```

---

## Adicionando novos dados e retreinando

```bash
# 1. Regenerar CSVs com novos dados
python -m etl.statsbomb_loader

# 2. Executar ETL e treinar
python run_pipeline.py --skip-etl   # se CSVs já existem
# ou
python run_pipeline.py              # desde o início

# 3. Exportar modelos atualizados
python -m delfos.serialization.export_models

# 4. Reiniciar a API
bash run_api.sh
```

Os modelos antigos no MLflow ficam preservados. O export pega sempre a versão mais recente do stage `None`.

---

## Métricas de avaliação (holdout — 10% dos dados, ~346 partidas)

| Modelo | Métrica | Valor |
|---|---|---|
| `total_goals` | MAE | 1.012 |
| `goals_distribution` | MAE | 0.211 |
| `corners` | MAE | 1.945 |
| `yellow_cards` | MAE | 1.403 |
| `red_cards` | MAE | 0.172 |
| `match_outcome` | Accuracy | — (pendente exportação) |

**Interpretação:**
- `total_goals MAE = 1.012`: em média, o modelo erra ~1 gol no total. Para uma linha de over/under 2.5, isso é funcional.
- `corners MAE = 1.945`: ~2 escanteios de erro médio. Linha de mercado típica é 9–10 escanteios.
- `yellow_cards MAE = 1.403`: ~1.4 cartões de erro. Linha de mercado típica é 3–4 cartões.

---

## Rastreamento de experimentos

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Acesse `http://localhost:5000` para visualizar todas as runs, parâmetros, métricas e artefatos.
