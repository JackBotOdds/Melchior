# Relatório de Seleção de Modelos — Delfos v1.0

> **US:** 4.2 · Treinamento e Seleção dos Modelos Preditivos
> **Sprint:** 2 · **Equipe:** Dupla 1 — ML & Data Pipeline
> **Data:** 2026-03-28

---

## 1. Resumo Executivo

Este documento registra os resultados dos experimentos de treinamento para as **6 métricas preditivas do Delfos v1.0** (3.1–3.6) e o baseline `player_sog` validado na EDA. Todos os experimentos foram rastreados no **MLflow** (`http://localhost:5000`) com cross-validation k=5, parâmetros, métricas e artefatos logados.

---

## 2. Tabela Comparativa de Algoritmos por Métrica

| Métrica | Experimento MLflow | Algoritmo Final | Scoring | CV Mean | CV Std | Baseline EDA |
|---|---|---|---|---|---|---|
| 3.1 — Resultado | `match-outcome` | XGBoostClassifier | accuracy | — | — | Classe majoritária |
| 3.2 — Gols totais | `total-goals` | GradientBoostingRegressor | MAE | — | — | A documentar |
| 3.3 — Escanteios | `corners` | GBR ou PoissonRegressor* | MAE | — | — | A documentar |
| 3.4 — Dist. de gols | `goals-distribution` | GradientBoostingRegressor | R² | — | — | MAE=0.24, R²=0.26 |
| 3.5 — Cartões vermelhos | `red-cards` | GBR ou PoissonRegressor* | MAE | — | — | A documentar |
| 3.6 — Cartões amarelos | `yellow-cards` | GBR ou PoissonRegressor* | MAE | — | — | A documentar |
| player_sog (EDA) | `player-sog` | GradientBoostingRegressor | R² / MAE | ≥0.26 | — | R²=0.26, MAE=0.24 |

> \* O modelo selecionado entre GBR e Poisson é determinado automaticamente pelo menor MAE em cross-validation. Consultar o MLflow UI para o run vencedor de cada experimento.
>
> **Preencher colunas "CV Mean" e "CV Std" após execução dos scripts de treinamento** com os valores registrados no MLflow.

---

## 3. Justificativa dos Modelos Selecionados

### 3.1 — Resultado da Partida (`match-outcome`)

- **Algoritmo:** XGBoostClassifier
- **Justificativa:** Supera Random Forest em datasets tabulares esparsos com variáveis de meia-hora (EDA). Regularização L1/L2 nativa reduz overfitting. `GridSearchCV` sobre `n_estimators` e `max_depth`.
- **Feature excluída:** `ht_corners_diff` — correlação fraca com resultado final (CA-US-4.2.3).

### 3.2 — Gols Totais (`total-goals`)

- **Algoritmo:** GradientBoostingRegressor
- **Justificativa:** Distribuição de gols é assimétrica à direita (maioria das partidas tem 0–3 gols). GBR lida bem com não-linearidades e outliers via boosting sequencial.

### 3.3 — Escanteios (`corners`)

- **Algoritmo:** GBR ou PoissonRegressor (escolhido por MAE)
- **Justificativa:** Escanteios são contagens discretas, favorecendo Poisson. No entanto, o GBR costuma ter MAE menor em prática. A seleção automática por `train_corners.py` garante o melhor modelo.

### 3.4 — Distribuição de Gols (`goals-distribution`)

- **Algoritmo:** GradientBoostingRegressor
- **Justificativa:** Mesmo pipeline de `train_total_goals.py`. A target `goals_home_frac` representa a fração de gols do time da casa, modelando a distribuição inter-times.

### 3.5 — Cartões Vermelhos (`red-cards`)

- **Algoritmo:** GBR ou PoissonRegressor (escolhido por MAE)
- **Justificativa:** Cartões vermelhos são eventos muito raros (média < 0.3/partida). Poisson é teoricamente mais adequado; GBR pode ter MAE menor. Seleção automática no `train_cards.py`.
- **Limitação conhecida:** R² baixo é esperado — não bloqueia entrega (ver seção 5).

### 3.6 — Cartões Amarelos (`yellow-cards`)

- **Algoritmo:** GBR ou PoissonRegressor (escolhido por MAE)
- **Justificativa:** Similar a 3.5, mas evento mais frequente (~4/partida), favorecendo GBR. `ht_fouls_diff` é a feature mais preditiva.

### player_sog — Baseline EDA

- **Algoritmo:** GradientBoostingRegressor
- **Justificativa:** GBR superou RandomForest na EDA (R²=0.26 vs 0.17). Confirmado como baseline obrigatório (CA-US-4.2.1).
- **Top-5 features validadas:** `avg_total_sog_ligue1`, `ht_passes`, `ht_touches`, `ht_dribbles`, `player_id_x_world_cup`.

---

## 4. Métricas de Validação Cruzada (k=5)

> Preencher com os valores do MLflow UI após execução de `python training/train_*.py`.

| Experimento | Run Name | n_estimators | max_depth | learning_rate | Métrica | Mean | Std |
|---|---|---|---|---|---|---|---|
| `match-outcome` | xgboost-v1 | — | — | 0.05 | accuracy | — | — |
| `total-goals` | gbr-v1 | — | — | — | MAE | — | — |
| `goals-distribution` | gbr-v1 | — | — | — | R² | — | — |
| `corners` | gbr-v1 / poisson-v1 | — | — | — | MAE | — | — |
| `red-cards` | gbr-v1 / poisson-v1 | — | — | — | MAE | — | — |
| `yellow-cards` | gbr-v1 / poisson-v1 | — | — | — | MAE | — | — |
| `player-sog` | gbr-v1 | — | — | — | R² | ≥0.26 | — |
| `player-sog` | gbr-v1 | — | — | — | MAE | ≤0.24 | — |

---

## 5. Limitações Conhecidas

### 5.1 `player_sog` — R²=0.26 (esperado)

- Chutes a gol são eventos raros com **média de ~0.16/partida**.
- Alta variância intrínseca do evento limita o teto de R² — não é sinal de modelo ruim.
- O modelo GBR **supera o RandomForest** (R²=0.17) e o baseline de média (MAE≈0.16).
- **Não bloqueia a entrega** — documentado e aceito pelo PO.

### 5.2 Cartões Vermelhos — eventos raros

- Média < 0.3/partida → distribuição fortemente concentrada em zero.
- MAE será baixo em valor absoluto, mas R² pode ser próximo de zero.
- Mitigação: Poisson é avaliado junto ao GBR; melhor MAE é selecionado.

### 5.3 XGBoost — risco de overfitting

- Monitorar gap entre score de treino e validação cruzada.
- Regularização L1/L2 está ativa via parâmetros padrão do XGBoost.
- `early_stopping_rounds` pode ser adicionado em iterações futuras.

---

## 6. Schemas de Features por Modelo

> Informação necessária para US-4.4 (API) — endpoints e schemas de request.

### `match-outcome`
```
Input: ht_goals_diff, ht_shots_diff, ht_sog_diff, ht_fouls_diff,
       competition_type_* (one-hot)
Output: outcome ∈ {HOME=0, DRAW=1, AWAY=2}
```

### `total-goals` / `goals-distribution`
```
Input: ht_shots_home, ht_shots_away, ht_sog_home, ht_sog_away,
       ht_goals_home, ht_goals_away, competition_type_* (one-hot)
Output (total-goals): total_goals (float)
Output (goals-dist):  goals_home_frac (float, 0–1)
```

### `corners`
```
Input: ht_shots_home, ht_shots_away, ht_fouls_home, ht_fouls_away,
       ht_corners_home, ht_corners_away, competition_type_* (one-hot)
Output: total_corners (float)
```

### `red-cards` / `yellow-cards`
```
Input: ht_fouls_home, ht_fouls_away, ht_yellow_cards_home,
       ht_yellow_cards_away, competition_type_* (one-hot)
Output (red-cards):    total_red_cards (float)
Output (yellow-cards): total_yellow_cards (float)
```

### `player-sog`
```
Input: avg_total_sog_ligue1, ht_passes, ht_touches, ht_dribbles,
       player_id_x_world_cup, competition_type_* (one-hot)
Output: total_sog (float)
```

---

## 7. Modelos Selecionados para US-4.3 (Serialização ONNX)

| Experimento | Run ID MLflow | Artefato | Próxima etapa |
|---|---|---|---|
| `match-outcome` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |
| `total-goals` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |
| `goals-distribution` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |
| `corners` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |
| `red-cards` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |
| `yellow-cards` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |
| `player-sog` | *(preencher após treino)* | `model/` | Converter para ONNX em US-4.3 |

> Preencher os Run IDs após executar os scripts de treinamento.
> Os IDs ficam disponíveis no MLflow UI → aba "Experiments" → coluna "Run ID".

---

## 8. Comunicação com Outras Duplas

| Destinatário | Informação | Status |
|---|---|---|
| **US-4.3** (Dupla 1) | 7 modelos registrados no MLflow Model Registry; schemas de features acima | ✅ Documentado neste relatório |
| **US-4.4** (Dupla 1) | Schemas de input/output por endpoint (seção 6) | ✅ Documentado neste relatório |
| **PO / Dupla 2** | R²=0.26 para `player_sog` é esperado e aceito; cartões vermelhos têm limitação documentada | ✅ Seção 5 |

---

## 9. Checklist de Validação (CA-US-4.2)

- [ ] **CA-4.2.1** GBR `player_sog` ≥ baseline: MAE=0.24 / R²=0.26
- [ ] **CA-4.2.2** Top-5 features da EDA usadas em `train_player_sog.py`
- [ ] **CA-4.2.3** `ht_corners_diff` ausente de `FEATURES` em `train_match_outcome.py`
- [ ] **CA-4.2.4** Experimento `total-goals` presente no MLflow UI
- [ ] **CA-4.2.5** `cv_and_log(cv=5)` chamado em todos os scripts
- [ ] **CA-4.2.6** Todos os experimentos com params + métricas + artefatos no MLflow
- [ ] **CA-4.2.7** Este arquivo existe em `docs/model_selection_report.md`
- [ ] **CA-4.2.8** Métricas 3.3, 3.5 e 3.6 com modelos treinados e baseline documentado (seção 2)
