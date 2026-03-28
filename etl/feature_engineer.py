import pandas as pd

def engineer(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Realiza a engenharia de features com foco em evitar Data Leakage 
    através de ordenação temporal e uso de shift em médias móveis.
    """
    engineered_dfs = {}

    context_mapping = {
        "wc2022": "World Cup",
        "ligue1_2021_2022": "Ligue 1"
    }

    for name, df in dfs.items():
        current_df = df.copy()

        # Mapeamento de tipo de competição para todos os DataFrames
        if "source_context" in current_df.columns:
            current_df["competition_type"] = current_df["source_context"].map(context_mapping)

        # Regras exclusivas para o DataFrame player_sog
        if name == "player_sog":
            # 1 & 2. Features de interação (ID x Contexto)
            current_df["player_id_x_world_cup"] = 0
            current_df.loc[current_df["competition_type"] == "World Cup", "player_id_x_world_cup"] = current_df["player_id"]
            
            current_df["player_id_x_ligue_1"] = 0
            current_df.loc[current_df["competition_type"] == "Ligue 1", "player_id_x_ligue_1"] = current_df["player_id"]

            # 3. Evitar Leakage: Ordenar obrigatoriamente por match_date
            if "match_date" in current_df.columns:
                current_df["match_date"] = pd.to_datetime(current_df["match_date"])
                current_df = current_df.sort_values("match_date")

            # 4. Cálculo de avg_total_sog_ligue1 com shift(1) para evitar look-ahead bias
            ligue1_mask = current_df["competition_type"] == "Ligue 1"
            
            # Calculamos a média expandida apenas no subset da Ligue 1
            # O transform(lambda x: ...) garante que o cálculo respeite o agrupamento por jogador
            current_df.loc[ligue1_mask, "avg_total_sog_ligue1"] = (
                current_df[ligue1_mask]
                .groupby("player_id")["total_sog"]
                .transform(lambda x: x.expanding().mean().shift(1))
            )
            
            # 5. Preencher NaNs com 0 (casos da primeira partida ou outras competições)
            current_df["avg_total_sog_ligue1"] = current_df["avg_total_sog_ligue1"].fillna(0)

        engineered_dfs[name] = current_df

    return engineered_dfs
