# Bloco 1 — registro factual de ciclos

Autorização: até 15 ciclos, com checkpoint humano a cada 5. Este bloco executa os ciclos 1–5. Não são chamadas ao runner nem 15 execuções de API. PO/Arquiteto, Dev, QA e TL trabalham como agentes desta sessão. Sem merge ou exposição pública.

## Ciclo 1 — modelo, regras e primeiro QA

- PO/Arquitetura: `PLAN.md`; entidades cluster/squad/projeto/marco e grafo fornecedor→consumidor. Aplicativo estático individual, armazenamento local.
- Dev: primeiro `core.js` com schema whitelist, datas, DAG, backup normalizado, CSV e saúde.
- QA independente: primeira execução 11/11; ao confrontar com o critério de produto, corrigiu o próprio teste de saúde sem marcos, resultando em 10/11. O teste passou a reproduzir o defeito real.
- TL independente: dois achados médios — sem marcos rotulado como no prazo e campos de previsão/conclusão real ausentes. Evidências em `REVIEW.md`.
- Decisão: AJUSTES_OBRIGATORIOS. Não liberar esta base para homologação; corrigir no ciclo 2.

Os ciclos seguintes serão registrados somente após suas evidências.
