import pandas as pd

def clean(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Realiza a limpeza dos DataFrames: remove colunas constantes e trata valores nulos em campos numéricos.
    """
    cleaned_dfs = {}

    for name, df in dfs.items():
        current_df = df.copy()

        # Regra 1: Remover ht_corners_diff de team_outcome (coluna com std=0)
        if name == "team_outcome" and "ht_corners_diff" in current_df.columns:
            current_df = current_df.drop(columns=["ht_corners_diff"])

        # Regra 2: Identificar colunas numéricas e preencher NaNs com a mediana
        numeric_cols = current_df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if current_df[col].isnull().any():
                median_value = current_df[col].median()
                current_df[col] = current_df[col].fillna(median_value)

        cleaned_dfs[name] = current_df

    return cleaned_dfs
