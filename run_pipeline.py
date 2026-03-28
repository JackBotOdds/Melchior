"""
run_pipeline.py - Pipeline completo Delfos v1.0

Etapas:
  1. StatsBomb JSON -> CSV  (etl/statsbomb_loader.py)
  2. ETL: CSV -> Parquet, split 90/10, StandardScaler  (etl/pipeline.py)
  3. Treinar modelos + avaliar no holdout com relatório CLI + gráficos

Uso:
  python run_pipeline.py              # executa tudo
  python run_pipeline.py --skip-etl  # pula download e ETL (dados já existem)

Gráficos gerados em: reports/plots/
MLflow local em:     mlflow.db  (visualizar com: mlflow ui --backend-store-uri sqlite:///mlflow.db)
"""

import sys
import argparse
from pathlib import Path

# Garante que root e delfos/ estão no path para todos os imports
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "delfos"))


def run_etl():
    print("\n" + "-" * 60)
    print("ETAPA 1 - StatsBomb JSON -> CSV")
    print("-" * 60)
    from etl.statsbomb_loader import build_raw_csvs
    build_raw_csvs()

    print("\n" + "-" * 60)
    print("ETAPA 2 - ETL: CSV -> Parquet + split 90/10 + StandardScaler")
    print("-" * 60)
    from etl.data_loader import load_all
    from etl.cleaner import clean
    from etl.feature_engineer import engineer
    from etl.preprocessor import fit_and_split

    raw_dir   = ROOT / "data" / "raw"
    proc_dir  = ROOT / "data" / "processed"
    prep_dir  = ROOT / "models" / "preprocessors"

    dfs = load_all(raw_dir)
    dfs = clean(dfs)
    dfs = engineer(dfs)
    fit_and_split(dfs, prep_dir, proc_dir)
    print("  ETL concluído.")


def run_training():
    print("\n" + "-" * 60)
    print("ETAPA 3 - Treinamento + Avaliação no Holdout")
    print("-" * 60)

    from training.train_match_outcome import train as t1
    from training.train_total_goals   import train as t2
    from training.train_corners       import train as t3
    from training.train_cards         import train as t4
    from training.train_player_sog    import train as t5

    t1()
    t2()
    t3()
    t4()
    t5()


def main():
    parser = argparse.ArgumentParser(description="Delfos v1.0 - Pipeline completo")
    parser.add_argument(
        "--skip-etl", action="store_true",
        help="Pula download StatsBomb e ETL (use quando os parquets já existem)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("     DELFOS v1.0 -- PIPELINE DE TREINAMENTO")
    print("=" * 60)

    if not args.skip_etl:
        run_etl()
    else:
        print("\n[--skip-etl] Etapas 1 e 2 puladas.")

    run_training()

    print("\n" + "=" * 60)
    print("  PIPELINE CONCLUIDO")
    print("  Graficos : reports/plots/")
    print("  MLflow   : mlflow ui --backend-store-uri sqlite:///mlflow.db")
    print("  Modelos  : models/trained/")
    print("=" * 60)


if __name__ == "__main__":
    main()
