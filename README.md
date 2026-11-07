# Otimizar Rota de Entrega

Ferramenta para auditoria, consolidação e otimização de rotas de entrega a partir de planilhas (ex.: Shopee), com padronização de endereços e CEP via ViaCEP, geração de planilha final e relatório visual por bairro/rua.

## Uso

1. Coloque a planilha (`.xlsx`) na pasta de entrada.
2. Execute o pipeline:

```bash
python scripts/run_pipeline.py "caminho/para/planilha.xlsx"
```

3. Saídas geradas:
   - `*- otimizado.xlsx` (abas: Dados Originais, Planilha Final, Coordenadas Suspeitas, CEPs Faltantes, ViaCEP, Auditoria, Relatório Visual)
   - `Relatorio Visual - Rota de Entrega.md`
   - `Relatorio Visual - Rota de Entrega.png`

## Requisitos

- Python 3.10+
- openpyxl, easyocr, Pillow, requests (ou urllib)
- (Opcional) geocodebr — geocodificação brasileira via CNEFE/IBGE para validar/enriquecer coordenadas

## Prompt

O prompt completo está em `prompt.md`.