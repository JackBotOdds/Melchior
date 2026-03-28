import pandas as pd

def engineer(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Realiza a engenharia de features com foco em evitar Data Leakage 
    através de ordenação temporal e uso de shift em médias móveis.
    """
    engineered_dfs = {}

    # Mapeamento legado: CSVs wc2022_* e ligue1_2021_2022_* não têm competition_type.
    # Usa os mesmos valores do statsbomb_loader para consistência nos get_dummies.
    context_mapping = {
        "wc2022":            "World Cup",
        "ligue1_2021_2022":  "Domestic League",
    }

    for name, df in dfs.items():
        current_df = df.copy()

        # competition_type: três casos possíveis ao concatenar CSVs novos e legados:
        # 1. Coluna ausente (dados 100% legados) → cria via source_context
        # 2. Coluna presente com NaN (mix de legado + novo) → preenche NaN via source_context
        # 3. Coluna presente sem NaN (dados 100% novos) → não faz nada
        if "competition_type" not in current_df.columns:
            if "source_context" in current_df.columns:
                current_df["competition_type"] = (
                    current_df["source_context"].map(context_mapping).fillna("Other")
                )
            else:
                current_df["competition_type"] = "Other"
        elif current_df["competition_type"].isna().any() and "source_context" in current_df.columns:
            mask = current_df["competition_type"].isna()
            current_df.loc[mask, "competition_type"] = (
                current_df.loc[mask, "source_context"].map(context_mapping).fillna("Other")
            )

        # Regras exclusivas para o DataFrame player_sog
        if name == "player_sog":
            # Mascara baseada em source_context para ser robusto a qualquer valor de competition_type
            is_wc = current_df["source_context"].str.contains("wc|world_cup|comp43", case=False, na=False)

            # Feature de interação: player_id x Copa do Mundo
            current_df["player_id_x_world_cup"] = 0
            current_df.loc[is_wc, "player_id_x_world_cup"] = current_df.loc[is_wc, "player_id"]

        engineered_dfs[name] = current_df

    return engineered_dfs
