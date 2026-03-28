import pickle
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

HOLDOUT_SIZE = 0.15
HOLDOUT_SEED = 42

def fit_and_split(dfs: dict[str, pd.DataFrame], preprocessors_dir: Path, processed_dir: Path):
    """
    Realiza o split treino/holdout, normaliza colunas numéricas (evitando leakage ao fitar apenas no treino)
    e persiste os scalers e os dados processados.
    """
    # Garantir que os diretórios existam
    preprocessors_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    for name, df in dfs.items():
        # 1. Identificar colunas numéricas
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        
        # 2. Split de treino e holdout com estratificação por competition_type
        train_df, holdout_df = train_test_split(
            df, 
            test_size=HOLDOUT_SIZE, 
            random_state=HOLDOUT_SEED,
            stratify=df["competition_type"]
        )

        # 3. StandardScaler: Fit/Transform no treino, Transform no holdout
        scaler = StandardScaler()
        
        # Criamos cópias para não alterar os originais acidentalmente durante a atribuição
        train_df = train_df.copy()
        holdout_df = holdout_df.copy()
        
        train_df[numeric_cols] = scaler.fit_transform(train_df[numeric_cols])
        holdout_df[numeric_cols] = scaler.transform(holdout_df[numeric_cols])

        # 4. Salvar o scaler via pickle
        scaler_path = preprocessors_dir / f"scaler_{name}.pkl"
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)

        # 5. Salvar DFs em formato parquet
        train_df.to_parquet(processed_dir / f"{name}_train.parquet", index=False)
        holdout_df.to_parquet(processed_dir / f"{name}_holdout.parquet", index=False)

        # 6. Logs de execução
        print(f"[{name}] Train: {len(train_df)} | Holdout: {len(holdout_df)} | Scaler: {scaler_path.name}")
