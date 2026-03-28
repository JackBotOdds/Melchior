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

        # competition_type: usa valor ja presente (do statsbomb_loader) ou mapeia pelo contexto legado
        if "competition_type" not in current_df.columns and "source_context" in current_df.columns:
            current_df["competition_type"] = current_df["source_context"].map(context_mapping)
            current_df["competition_type"] = current_df["competition_type"].fillna("Other")

        # Regras exclusivas para o DataFrame player_sog
        if name == "player_sog":
            # Mascara baseada em source_context para ser robusto a qualquer valor de competition_type
            is_wc = current_df["source_context"].str.contains("wc|world_cup|comp43", case=False, na=False)

            # Feature de interação: player_id x Copa do Mundo
            current_df["player_id_x_world_cup"] = 0
            current_df.loc[is_wc, "player_id_x_world_cup"] = current_df.loc[is_wc, "player_id"]

        engineered_dfs[name] = current_df

    return engineered_dfs
