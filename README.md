# Rota de Entrega — Versão Automatizada

Versão automatizada da ferramenta de auditoria, consolidação e otimização de rotas de entrega.
Mantém tudo o que já existe no projeto original e adiciona **atualização automática dos dados** (cron mensal) e **verificação de versão** no aplicativo web.

## Organograma (Arquitetura)

```mermaid
flowchart TD
    A[Usuário / Smartphone] -->|Upload .xlsx| B[Web App (GitHub Pages)]
    B --> C[Processamento no Navegador (JS)]
    C --> D[ViaCEP API]
    C --> E[Nominatim/OSM - geocodificação opcional]
    C --> F[Parquet CNEFE (Hugging Face) - DuckDB-WASM]
    C --> G[Planilha otimizada .xlsx]
    C --> H[Relatório visual .png/.md]

    I[GitHub Actions - Cron Mensal] --> J[scripts/update_data.py]
    J --> K[geocodebr - CNEFE/IBGE]
    J --> L[Hugging Face - Parquet atualizado]
    J --> M[version.json]
    M --> N[Web App verifica versão]
    N -->|nova versão| A

    O[Pipeline Python local] -->|flag --geocode| K
    O --> G
```

## Componentes

1. **Web App (GitHub Pages)** — `index.html`
   - Upload de planilha, processamento no navegador, download dos arquivos.
   - Consulta ViaCEP e, opcionalmente, Nominatim/OSM ou DuckDB-WASM (Parquet CNEFE).
   - Verifica `version.json` e avisa quando há nova versão dos dados.

2. **Pipeline Python** — `scripts/run_pipeline.py`
   - Auditoria, padronização, ViaCEP, consolidação, planilha final, relatório.
   - Flag `--geocode` para usar `geocodebr` (CNEFE/IBGE) para coordenadas precisas.

3. **Atualização Automática** — `.github/workflows/update-data.yml`
   - Cron mensal (dia 1, 03:00 UTC).
   - Roda `scripts/update_data.py`: baixa CNEFE, filtra por município, gera Parquet, publica no Hugging Face, atualiza `version.json`.
   - Totalmente automático (sem intervenção humana).

4. **Dados** — `version.json` + Parquet no Hugging Face
   - Versionamento para o app detectar atualizações.
   - Parquet consultável via DuckDB-WASM no navegador.

## Como usar

### Web (smartphone ou desktop)
Acesse: https://marcosantoniosantos.github.io/rota-entrega-auto/

### Pipeline Python
```bash
python scripts/run_pipeline.py planilha.xlsx
# com geocodificação precisa (geocodebr):
python scripts/run_pipeline.py planilha.xlsx --geocode
```

## Requisitos

- Python 3.10+ (pipeline)
- Navegador moderno (web app)
- (Opcional) geocodebr para máxima precisão

## Repositório original

Este projeto mantém o original intacto: https://github.com/MarcosAntonioSantos/rota-entrega-tool
EOF