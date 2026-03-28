import argparse
from pathlib import Path
from etl.data_loader import load_all
from etl.cleaner import clean
from etl.feature_engineer import engineer
from etl.preprocessor import fit_and_split

def main():
    """
    Orquestrador principal do Pipeline ETL.
    Coordena o fluxo de dados desde a carga bruta até a persistência de holdouts normalizados.
    """
    parser = argparse.ArgumentParser(description="JackBot ETL Pipeline")
    parser.add_argument(
        "--input", 
        type=str, 
        default="data/raw/", 
        help="Diretório contendo os CSVs originais"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="data/processed/", 
        help="Diretório para salvar os arquivos Parquet processados"
    )
    parser.add_argument(
        "--preprocessors", 
        type=str, 
        default="models/preprocessors/", 
        help="Diretório para salvar os scalers (objetos pkl)"
    )

    args = parser.parse_args()
    
    # Conversão para Path objects
    input_path = Path(args.input)
    output_path = Path(args.output)
    preprocessors_path = Path(args.preprocessors)

    print(">>> Iniciando Pipeline ETL...")

    # 1. Carga
    print("Carregando dados...")
    dfs = load_all(input_path)

    # 2. Limpeza
    print("Limpando dados...")
    dfs = clean(dfs)

    # 3. Engenharia de Features
    print("Engenharia de Features...")
    dfs = engineer(dfs)

    # 4. Pré-processamento e Divisão
    print("Pré-processamento e Split...")
    fit_and_split(dfs, preprocessors_path, output_path)

    print(">>> Pipeline concluído com sucesso!")

if __name__ == "__main__":
    main()
