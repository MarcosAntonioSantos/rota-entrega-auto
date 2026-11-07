"""Atualiza o Parquet do CNEFE (município) no Hugging Face e version.json."""
import os, json, datetime
import geocodebr

MUNICIPIO = "Anapolis"
ESTADO = "GO"

def main():
    # Exemplo: geocodificar um conjunto de CEPs do município para gerar o Parquet
    # Aqui você pode adaptar para baixar/filtrar o CNEFE conforme necessário.
    from geocodebr import busca_por_cep
    # Exemplo de CEPs do município (substitua pela lista real)
    ceps = []
    resultado = busca_por_cep(cep=ceps, verboso=False)
    df = resultado.to_pandas() if hasattr(resultado, 'to_pandas') else resultado

    # Salvar Parquet local
    out_path = "data/municipio.parquet"
    os.makedirs("data", exist_ok=True)
    df.to_parquet(out_path, index=False)

    # Upload para Hugging Face
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        api.upload_file(
            path_or_fileobj=out_path,
            path_in_repo="municipio.parquet",
            repo_id="MarcosAntonioSantos/rota-entrega-dados",
            repo_type="dataset",
        )
        print("Upload para Hugging Face concluído.")

    # Atualizar version.json
    version = {
        "version": datetime.date.today().isoformat(),
        "municipio": MUNICIPIO,
        "estado": ESTADO,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version, f, indent=2, ensure_ascii=False)
    print("version.json atualizado:", version)

if __name__ == "__main__":
    main()
EOF