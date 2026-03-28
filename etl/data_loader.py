import pandas as pd
from pathlib import Path

GRANULARITIES = ["team_outcome", "team_sog", "player_sog"]

def load_all(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Descobre automaticamente todos os CSVs em raw_dir que correspondam
    ao padrao *_{granularidade}.csv e combina em um DataFrame por granularidade.
    Compativel tanto com CSVs nomeados por competicao (gerados pelo statsbomb_loader)
    quanto com os nomes legados (wc2022_*, ligue1_*).
    """
    raw_dir = Path(raw_dir)
    result  = {}

    for gran in GRANULARITIES:
        csv_files = sorted(raw_dir.glob(f"*_{gran}.csv"))

        if not csv_files:
            raise FileNotFoundError(
                f"Nenhum arquivo CSV encontrado em '{raw_dir}' para '{gran}'.\n"
                "Execute primeiro: python -m etl.statsbomb_loader"
            )

        frames = []
        for path in csv_files:
            df  = pd.read_csv(path)
            ctx = path.stem[: -len(f"_{gran}")]   # extrai contexto do nome do arquivo
            if "source_context" not in df.columns:
                df["source_context"] = ctx
            frames.append(df)

        result[gran] = pd.concat(frames, ignore_index=True)

    return result
