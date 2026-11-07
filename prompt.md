# AUDITORIA, CONSOLIDAÇÃO E OTIMIZAÇÃO DE ROTA DE ENTREGA

Analise integralmente a planilha anexada e execute uma auditoria logística completa dos dados.

## REGRAS OBRIGATÓRIAS

1. NÃO excluir nenhuma linha, registro, entrega, pedido ou pacote existente na planilha.
2. NÃO incluir dados que não estejam presentes no arquivo.
3. NÃO inventar informações.
4. NÃO presumir dados ausentes.
5. NÃO alterar códigos de rastreamento, números de pacotes, identificadores, destinatários ou qualquer informação original sem justificar claramente a alteração.
6. Sempre preservar uma cópia fiel dos dados originais, em uma aba própria, dentro da planilha.
7. Caso existam informações inconsistentes, incompletas ou suspeitas, sinalizar no relatório, mas nunca preencher com dados inventados.
8. Todas as conclusões devem ser baseadas exclusivamente nos dados presentes no arquivo.
9. Padronizar endereços e CEPs apenas para fins de análise, mantendo sempre referência ao dado original.
10. Juntar (consolidar) em uma única parada logística todos os pedidos/pacotes a serem entregues no mesmo endereço, mantendo todos os pedidos vinculados.

---

## OBJETIVOS DA ANÁLISE

### ETAPA 1 – AUDITORIA DOS DADOS

Verifique:

* Endereços duplicados.
* Endereços semelhantes com grafias diferentes.
* Possíveis erros de ortografia.
* CEPs incompatíveis.
* CEPs faltantes ou incompletos.
* Endereços sem CEP.
* Endereços incompletos (apenas CEP + logradouro) — revisão obrigatória.
* Coordenadas ausentes.
* Coordenadas duplicadas.
* Coordenadas incompatíveis com o endereço informado.
* Campos obrigatórios vazios.
* Registros potencialmente inconsistentes.
* Possíveis duplicidades de entrega/pedido.
* Diferenças de padronização entre registros.

Gerar uma lista detalhada dos problemas encontrados.

---

### ETAPA 2 – PADRONIZAÇÃO DE ENDEREÇOS E CEP

#### 2.1 Endereços

Padronize os endereços apenas para fins de análise logística, com o objetivo de localizar duplicidades. O endereço padronizado deve seguir o formato:

"Nome da rua, Qd. {quadra}, Lt. {lote}, nº {número}, {Observação}"

Abreviações padronizadas:

* Avenida → Av.
* Rua → Rua
* Travessa → Trav.
* Quadra → Qd.
* Lote → Lt.
* Número → nº

Regras:

* Quando não houver quadra, lote ou número, omitir o campo, mas sinalizar em Observações ("faltando quadra/lote/número").
* Identificar o logradouro (Rua/Av/Trav) mesmo quando aparecer após o nome do condomínio/residencial; nomes de condomínio/residencial/bairro (Residencial, Condomínio, Setor, Jardim, Vila, Parque) NÃO são observação — o bairro deve ser obtido da API ViaCEP.
* Normalizar variantes de abreviação encontradas: "kd"→"Qd.", "lt"→"Lt.", "lote"→"Lt.", "qd"→"Qd.".
* Não remover partes do nome da rua ao extrair Qd./Lt.; preservar nomes completos (ex.: "Rua Flor de Lins", "Rua Engenheiro Leonardo", "Rua Lucivanda").
* Aprender com diferenças de grafia (ex.: "Residencial Das Palmeiras, Sem, Rua bela vista kd d lote 15" → "Rua bela vista, Qd. D, Lt. 15", com bairro obtido via ViaCEP).
* Manter sempre uma referência ao endereço original.
* Remover diferenças causadas por maiúsculas/minúsculas, acentuação, espaços extras, pontuação inconsistente e erros de grafia.

#### 2.2 CEP

Padronizar o número do CEP para somente números (8 dígitos), conforme exigido pela API ViaCEP:

* Remover espaços, pontos, hífens e quaisquer caracteres não numéricos.
* Se o CEP possuir 8 dígitos, manter como "XXXXXXXX" (somente números).
* Se o CEP possuir menos de 8 dígitos ou mais de 8 dígitos, NÃO corrigir/inventar: marcar como "CEP incompleto" ou "CEP inválido" e sinalizar no relatório.
* Se o CEP estiver ausente/vazio, marcar como "CEP faltante" e sinalizar no relatório.
* Nunca inventar ou completar CEP.
* (Opcional) Para exibição, pode ser formatado como "00000-000", mas o valor padronizado utilizado nas consultas e agrupamentos deve ser somente números.

Manter sempre uma referência ao CEP original.

#### 2.2.1 Revisão de Endereços (Prioridade)

Antes de gerar coordenadas, revisar os endereços conforme níveis de prioridade:

1. CEP — chave principal para localizar o logradouro.
2. Logradouro (nome da rua) — deve ser compatível com o CEP (ViaCEP).
3. Número (nº) — se houver; ausência deve ser sinalizada.
4. Quadra (Qd.) — se houver; ausência deve ser sinalizada.
5. Lote (Lt.) — se houver; ausência deve ser sinalizada.

Regra de completude:

- Endereços compostos apenas por CEP + nome do logradouro são INCOMPLETOS e devem ser revistos obrigatoriamente antes da geocodificação.
- Ausência de número/quadra/lote deve ser sinalizada em Observações ("faltando número/quadra/lote").

#### 2.3 Consulta à API ViaCEP

Para cada CEP presente e válido, consultar a API ViaCEP (https://viacep.com.br/ws/{CEP}/json/) para obter logradouro, bairro, localidade, UF e CEP padronizado. O {CEP} deve ser enviado somente com números (8 dígitos), sem hífen.

Regras:

* Utilizar os dados retornados como referência para padronização de endereço, bairro e cidade.
* Comparar o bairro/logradouro da planilha com o retornado; sinalizar divergências no relatório.
* Se a API retornar erro ou CEP não encontrado, sinalizar no relatório, sem inventar dados.
* Se o CEP estiver faltante/incompleto, não consultar; sinalizar.
* Respeitar limites de requisição (consultas sequenciais com pequeno intervalo).

---

### ETAPA 3 – IDENTIFICAÇÃO DE PRÉDIOS E CONDOMÍNIOS

Identifique automaticamente:

* Condomínios.
* Residenciais.
* Edifícios.
* Torres.
* Blocos.
* Conjuntos habitacionais.
* Loteamentos fechados.

Observação importante: Identifique se há entregas em estabelecimentos comerciais.

Quando múltiplos pedidos/pacotes possuírem o mesmo local físico de entrega (mesmo endereço padronizado OU mesmo prédio/condomínio/edifício/torre/bloco indicado no endereço):

* Considerar apenas UMA PARADA LOGÍSTICA.
* Manter TODOS os pedidos/pacotes vinculados à parada.
* Juntar (consolidar) os pedidos na mesma parada, sem perder nenhum.

Exemplo:

Parada 15
Condomínio Alfa
Pedido/Pacote 1
Pedido/Pacote 2
Pedido/Pacote 3
Pedido/Pacote 4

Resultado:
1 parada logística e 4 pedidos/pacotes.

---

### ETAPA 4 – CONSOLIDAÇÃO DAS PARADAS

Criar uma numeração de parada consolidada.

Regras:

* Mesmo endereço padronizado = mesma parada.
* Mesmo prédio = mesma parada.
* Mesmo condomínio = mesma parada.
* Mesma portaria de acesso = mesma parada.

Cada pedido/pacote deve permanecer individualizado, preservando o número de Sequence original.

Adicionar as colunas:

* Parada Consolidada
* Número original do Pedido/Pacote na Parada
* Quantidade Total de Pedidos/Pacotes da Parada

Exemplo:

Parada | Pedido/Pacote | Total
12 | 1 | 4
12 | 2 | 4
12 | 3 | 4
12 | 4 | 4

---

### ETAPA 5 – ANÁLISE DAS COORDENADAS

Verificar:

* Coordenadas ausentes.
* Coordenadas repetidas.
* Coordenadas incompatíveis com o endereço.
* Coordenadas compartilhadas por vários endereços.
* Possíveis erros de geocodificação.

Quando disponível, utilizar o pacote geocodebr (https://github.com/ipea/geocodebr) para geocodificar endereços e validar/enriquecer coordenadas (geocode, busca_por_cep), complementando o ViaCEP.

Gerar uma tabela específica chamada:

"Coordenadas Suspeitas"

Informando:

* Endereço
* Latitude
* Longitude
* Motivo da suspeita

---

### ETAPA 6 – OTIMIZAÇÃO DA ROTA

O objetivo principal é:

MINIMIZAR DESLOCAMENTOS DESNECESSÁRIOS.

Realizar:

* Agrupamento por rua, quadra e lote.
* Agrupamento geográfico.
* Agrupamento por proximidade.
* Agrupamento por condomínio.
* Agrupamento por edifício.
* Agrupamento por portaria.

Quando possível:

* Utilizar latitude e longitude.
* Utilizar lógica de roteirização.
* Evitar retornos desnecessários.
* Evitar cruzamentos repetidos da cidade.
* Reduzir quilometragem estimada.

---

### ETAPA 6.1 – SEPARAÇÃO POR BAIRRO E RUA (VIA CEP + ViaCEP)

Separar e agrupar a rota por bairro e por rua, utilizando o CEP como chave principal (CEP → bairro/rua), complementado pelos dados retornados pela API ViaCEP (logradouro, bairro, localidade).

Quando o CEP estiver ausente ou incompleto, utilizar o endereço padronizado para inferir bairro/rua e sinalizar no relatório.

Gerar agrupamentos visuais por bairro e, dentro de cada bairro, por rua, em ordem de rota.

---

### ETAPA 7 – PLANILHA FINAL

Gerar uma nova planilha contendo:

1. Ordem Otimizada da Rota
2. Parada Consolidada
3. Número original do Pedido/Pacote na Parada
4. Quantidade Total de Pedidos/Pacotes na Parada
5. Código do Pedido/Pacote
6. Sequence Original
7. Destinatário
8. Endereço Original
9. Endereço Padronizado (formato: Nome da rua, Qd., Lt., nº, Observação)
10. Bairro
11. Cidade
12. CEP (padronizado, somente números - 8 dígitos; se faltante/incompleto, sinalizar em Observações)
13. Latitude
14. Longitude
15. Observações

NÃO remover nenhuma informação existente na planilha original.

---

### ETAPA 8 – RELATÓRIO FINAL NO CHAT

Após concluir a análise, apresentar obrigatoriamente um relatório detalhado contendo:

#### Resumo Geral

* Quantidade total de registros.
* Quantidade total de pedidos/pacotes.
* Quantidade original de paradas.
* Quantidade final de paradas.
* Percentual de redução de paradas.

#### Problemas Encontrados

Listar:

* Erros de grafia.
* Endereços suspeitos.
* Coordenadas suspeitas.
* CEPs suspeitos.
* CEPs faltantes ou incompletos.
* Duplicidades.
* Registros incompletos.

#### Consolidações Realizadas

Informar:

* Quantos condomínios foram agrupados.
* Quantos prédios foram agrupados.
* Quantos endereços foram consolidados.
* Quantos pedidos/pacotes foram juntados por endereço comum.

#### Pontos de Atenção

Destacar qualquer situação que exija validação humana, incluindo CEPs faltantes/incompletos.

#### Relatório Visual Final (modelo: sequência de entregas)

Gerar um relatório visual contendo as separações por bairro e rua, no modelo:

- Título: "SEQUÊNCIA DAS ENTREGAS - ROTA COMPLETA".
- Total de paradas e total de pacotes.
- Legenda: Nº Shopee (parada original), Nº Azul (numeração própria de entrega), indicação de "mais de 1 pacote no mesmo endereço".
- Agrupamento por bairro (e rua), em ordem de rota, listando endereço e nº do pacote.
- Seção "RESUMO DAS PARADAS COM MAIS DE 1 PACOTE" listando os endereços consolidados com múltiplos pacotes.

#### Conclusão

Apresentar uma avaliação da qualidade dos dados e do potencial ganho logístico obtido com a otimização.

---

## VALIDAÇÃO FINAL OBRIGATÓRIA

Antes de concluir:

* Confirmar que nenhum registro foi excluído.
* Confirmar que nenhum pedido/pacote foi removido.
* Confirmar que nenhuma informação foi inventada.
* Confirmar que todos os pedidos/pacotes da planilha original permanecem presentes na planilha final.
* Confirmar que o número de Sequence original foi preservado para cada pacote.
* Confirmar que todos os CEPs foram padronizados para somente números (8 dígitos) ou sinalizados como faltantes/incompletos.
* Confirmar que todos os pedidos para o mesmo endereço foram consolidados em uma única parada.
* Confirmar que a rota foi separada por bairro e rua utilizando o CEP como chave.
* Confirmar que a API ViaCEP foi consultada para os CEPs válidos e divergências sinalizadas.
* Confirmar a geração do relatório visual final com as separações.
* Informar qualquer limitação encontrada durante a análise.