"""Atualiza version.json (sinaliza nova versão dos dados)."""
import os, json, datetime

def main():
    # Ler versão atual
    version_file = "version.json"
    try:
        with open(version_file, encoding="utf-8") as f:
            current = json.load(f)
    except Exception:
        current = {}

    new_version = datetime.date.today().isoformat()
    version = {
        "version": new_version,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "note": "Dados podem ter sido atualizados. O app detecta a nova versão e avisa o usuário.",
    }
    # preservar campos extras se existirem
    for k in ("municipio", "estado"):
        if k in current:
            version[k] = current[k]

    with open(version_file, "w", encoding="utf-8") as f:
        json.dump(version, f, indent=2, ensure_ascii=False)
    print("version.json atualizado:", version)

if __name__ == "__main__":
    main()
EOF