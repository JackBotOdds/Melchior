# Delfos API — Referência de Endpoints

**Base URL:** `http://localhost:8000`
**Docs interativos:** `http://localhost:8000/docs`
**Versão:** 1.0.0

---

## Autenticação

Nenhuma autenticação é necessária nos endpoints do Delfos. O token da BetsAPI é configurado no servidor via variável de ambiente `BETSAPI_TOKEN` — o cliente não precisa enviá-lo.

---

## GET /health

Retorna o estado da API, modelos carregados e disponibilidade do feature store.

**Resposta 200:**
```json
{
  "status": "ok",
  "model_version": "1.0.0",
  "models_loaded": ["total_goals", "corners", "red_cards", "yellow_cards"],
  "store_ready": true
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | string | `"ok"` ou `"degraded"` |
| `model_version` | string | Versão do manifest ONNX |
| `models_loaded` | array | Modelos com sessão ONNX em memória |
| `store_ready` | boolean | true se team_outcome E team_sog estiverem carregados |

---

## POST /v1/predict/total-goals

Prediz o total de gols esperados no jogo completo.

**Body:**
```json
{
  "match_id": "3829431"
}
```

**Resposta 200:**
```json
{
  "expected_goals": 2.4532,
  "over_25_probability": 0.4441,
  "under_25_probability": 0.5559,
  "most_likely_range": "2-3",
  "confidence_score": 0.5559,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T09:26:54.160801Z"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `expected_goals` | float | Valor esperado pelo modelo (regressão) |
| `over_25_probability` | float | P(gols > 2.5) via distribuição Poisson |
| `under_25_probability` | float | P(gols ≤ 2.5) = 1 - over_25 |
| `most_likely_range` | string | `"0-1"`, `"2-3"` ou `"4+"` |
| `confidence_score` | float | max(over_25, under_25) |

---

## POST /v1/predict/corners

Prediz o total de escanteios esperados no jogo completo.

**Body:**
```json
{
  "match_id": "3829431"
}
```

**Resposta 200:**
```json
{
  "expected_corners": 7.3398,
  "over_9_probability": 0.2056,
  "under_9_probability": 0.7944,
  "confidence_score": 0.7944,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T09:26:54.411502Z"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `expected_corners` | float | Total esperado pelo modelo |
| `over_9_probability` | float | P(escanteios > 9) via Poisson |
| `under_9_probability` | float | P(escanteios ≤ 9) = 1 - over_9 |
| `confidence_score` | float | max(over_9, under_9) |

---

## POST /v1/predict/cards

Prediz cartões amarelos e vermelhos esperados no jogo completo.

**Body:**
```json
{
  "match_id": "3829431"
}
```

**Resposta 200:**
```json
{
  "expected_yellow_cards": 4.0391,
  "expected_red_cards": 0.0844,
  "over_3_yellow_probability": 0.5741,
  "under_3_yellow_probability": 0.4259,
  "confidence_score": 0.5741,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T09:26:54.668502Z"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `expected_yellow_cards` | float | Cartões amarelos esperados |
| `expected_red_cards` | float | Cartões vermelhos esperados (tipicamente < 0.3) |
| `over_3_yellow_probability` | float | P(amarelos > 3) via Poisson |
| `under_3_yellow_probability` | float | P(amarelos ≤ 3) |
| `confidence_score` | float | max das probabilidades de cartão amarelo |

---

## POST /v1/predict/match-outcome

Probabilidades de resultado (vitória casa / empate / vitória visitante).

**Status atual:** HTTP 503. Modelo não carregado por incompatibilidade de exportação ONNX.

**Body:**
```json
{
  "match_id": "3829431"
}
```

**Resposta 200 (quando disponível):**
```json
{
  "home_win_probability": 0.5821,
  "draw_probability": 0.2344,
  "away_win_probability": 0.1835,
  "favorite_outcome": "HOME",
  "confidence_score": 0.5821,
  "model_version": "1.0.0",
  "generated_at": "2026-03-28T10:00:00Z"
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `home_win_probability` | float | P(equipe da casa vence) |
| `draw_probability` | float | P(empate) |
| `away_win_probability` | float | P(visitante vence) |
| `favorite_outcome` | string | `"HOME"`, `"DRAW"` ou `"AWAY"` |
| `confidence_score` | float | Probabilidade máxima entre as três classes |

---

## Endpoints Live — features manuais

Os endpoints `/v1/predict/live/*` aceitam as mesmas respostas dos endpoints `/betsapi/*`, mas recebem as features diretamente no body em vez de buscá-las na BetsAPI.

### Body: LiveMatchRequest

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

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `competition_type` | string | `"Domestic League"` | Tipo de competição. Valores aceitos: `"Domestic League"`, `"World Cup"`, `"Continental"` |
| `ht_goals_home` | float | 0 | Gols marcados pela equipe da casa no 1º tempo |
| `ht_goals_away` | float | 0 | Gols marcados pela equipe visitante no 1º tempo |
| `ht_shots_home` | float | 0 | Total de chutes da equipe da casa no 1º tempo |
| `ht_shots_away` | float | 0 | Total de chutes da equipe visitante no 1º tempo |
| `ht_sog_home` | float | 0 | Chutes no alvo da equipe da casa |
| `ht_sog_away` | float | 0 | Chutes no alvo da equipe visitante |
| `ht_fouls_home` | float | 0 | Faltas cometidas pela equipe da casa |
| `ht_fouls_away` | float | 0 | Faltas cometidas pela equipe visitante |
| `ht_corners_home` | float | 0 | Escanteios da equipe da casa |
| `ht_corners_away` | float | 0 | Escanteios da equipe visitante |
| `ht_yellow_cards_home` | float | 0 | Cartões amarelos da equipe da casa |
| `ht_yellow_cards_away` | float | 0 | Cartões amarelos da equipe visitante |

Os valores são normalizados automaticamente pelo servidor via StandardScaler antes da inferência.

Endpoints disponíveis:
- `POST /v1/predict/live/total-goals` → `TotalGoalsResponse`
- `POST /v1/predict/live/corners` → `CornersResponse`
- `POST /v1/predict/live/cards` → `CardsResponse`
- `POST /v1/predict/live/match-outcome` → `MatchOutcomeResponse` *(503 — pendente)*

---

## Endpoints BetsAPI

Os endpoints `/v1/predict/betsapi/*` buscam automaticamente as estatísticas ao vivo na BetsAPI e executam a predição.

### Body: BetsAPIRequest

```json
{
  "fi": "12345678",
  "competition_type": "Domestic League"
}
```

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `fi` | string | — | Fixture ID do jogo ao vivo na BetsAPI. **Obrigatório.** |
| `competition_type` | string | `"Domestic League"` | Tipo de competição. Impacta a predição via feature one-hot. |

**Como obter o `fi`:**
```
GET https://api.b365api.com/v1/bet365/inplay?token=TOKEN
```
Filtre por `sport_id=1` e copie o campo `fi` do evento desejado.

Endpoints:
- `POST /v1/predict/betsapi/total-goals` → `TotalGoalsResponse`
- `POST /v1/predict/betsapi/corners` → `CornersResponse`
- `POST /v1/predict/betsapi/cards` → `CardsResponse`
- `POST /v1/predict/betsapi/match-outcome` → `MatchOutcomeResponse` *(503 — pendente)*

---

## Códigos de status HTTP

| Código | Quando ocorre |
|---|---|
| `200 OK` | Predição realizada com sucesso |
| `400 Bad Request` | `match_id` não é numérico |
| `404 Not Found` | `match_id` não existe no feature store, ou `fi` não encontrado na BetsAPI |
| `422 Unprocessable Entity` | Jogo fora da janela HT (2º tempo, final, prorrogação) |
| `503 Service Unavailable` | Modelo ONNX não carregado, ou BetsAPI indisponível/timeout |

---

## Notas de integração para o frontend

1. **Endpoint principal:** Para jogos ao vivo, use sempre os endpoints `/v1/predict/betsapi/*` — eles fazem tudo automaticamente a partir do `fi`.

2. **`competition_type`:** Afeta a predição via feature one-hot. Envie o valor correto conforme o jogo:
   - Ligas nacionais (Premier League, La Liga, etc.) → `"Domestic League"`
   - Copa do Mundo → `"World Cup"`
   - Champions League, Copa Libertadores, etc. → `"Continental"`

3. **Erro 422:** Significa que o jogo já passou do intervalo. Os modelos são treinados para predizer a partir do 1º tempo/intervalo. Não envie requisições para jogos no 2º tempo.

4. **match_outcome (503):** Trate com graceful degradation no frontend — exiba "indisponível" em vez de mostrar erro ao usuário.

5. **`confidence_score`:** Valor entre 0 e 1. Indica a "certeza" da predição. Abaixo de 0.6 sugere jogo equilibrado; acima de 0.75 sugere predição mais confiante. Use para calibrar a exibição (ex: intensidade de cor, badge de confiança).

6. **Polling:** Se o frontend precisar atualizar as predições durante o jogo, recomenda-se polling a cada 2–5 minutos — não a cada segundo. As estatísticas da BetsAPI atualizam em tempo semi-real, mas predições com diferença de 1–2 minutos raramente mudam significativamente.
