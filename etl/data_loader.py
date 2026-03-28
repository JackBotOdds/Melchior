import pandas as pd
from pathlib import Path

GRANULARITIES = ["team_outcome", "team_sog", "player_sog"]
CONTEXTS = ["wc2022", "ligue1_2021_2022"]

def load_all(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Lê os arquivos CSV das granularidades e contextos especificados,
    adiciona metadados de rastreabilidade e retorna os DataFrames combinados.
    """
    results = {}

    for granularity in GRANULARITIES:
        dataframes = []
        for context in CONTEXTS:
            file_path = raw_dir / f"{context}_{granularity}.csv"
            
            # Leitura do CSV
            df = pd.read_csv(file_path)
            
            # Adição da coluna de rastreabilidade
            df["source_context"] = context
            
            dataframes.append(df)
        
        # Consolidação dos contextos para a granularidade atual
        results[granularity] = pd.concat(dataframes, ignore_index=True)
        
    return results
