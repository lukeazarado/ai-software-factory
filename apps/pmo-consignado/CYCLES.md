# Bloco 1 — registro factual de ciclos

Autorização: até 15 ciclos, com checkpoint humano a cada 5. Este bloco executa os ciclos 1–5. Não são chamadas ao runner nem 15 execuções de API. PO/Arquiteto, Dev, QA e TL trabalham como agentes desta sessão. Sem merge ou exposição pública.

## Ciclo 1 — modelo, regras e primeiro QA

- PO/Arquitetura: `PLAN.md`; entidades cluster/squad/projeto/marco e grafo fornecedor→consumidor. Aplicativo estático individual, armazenamento local.
- Dev: primeiro `core.js` com schema whitelist, datas, DAG, backup normalizado, CSV e saúde.
- QA independente: primeira execução 11/11; ao confrontar com o critério de produto, corrigiu o próprio teste de saúde sem marcos, resultando em 10/11. O teste passou a reproduzir o defeito real.
- TL independente: dois achados médios — sem marcos rotulado como no prazo e campos de previsão/conclusão real ausentes. Evidências em `REVIEW.md`.
- Decisão: AJUSTES_OBRIGATORIOS. Não liberar esta base para homologação; corrigir no ciclo 2.

## Ciclo 2 — correção do modelo e interface funcional

- PO/Arquitetura: preservar planejamento original, separar previsão e conclusão real, estado Sem marcos explícito.
- Dev: UI de portfólio, organização, marcos, vínculos, cronograma, painel e exportação; campos de previsão/justificativa e conclusão real adicionados ao schema. Controles de texto ampliados.
- QA: testes do core reexecutados pelo Dev (12/12 na ocasião); navegador confirmou criação e persistência do projeto após recarregar e Sem marcos após correção.
- TL: achados do ciclo 1 resolvidos; parecer APROVADO delimitado para seguir integração, sem equivaler a aprovação de PR.

## Ciclo 3 — integração, segurança de dados e dependências

- PO/Arquitetura: impactos potenciais não podem atravessar marcos já concluídos como se fossem bloqueios pendentes.
- Dev: propagação operacional corrigida para parar em intermediários concluídos; diálogo nomeado e erro focado.
- QA independente: 21/21 testes reais (14 domínio e 7 integração VM). A integração cobre inicialização, leitura corrompida/bloqueada, falha de gravação, importação inválida/cancelada/válida e tamanho excessivo.
- QA navegador: mapa exibe clusters/squads dos dois lados; ciclo transitivo m4→m1 rejeitado sem limpar selects; Escape fecha o diálogo. Relatório gerado no DOM excluiu a nota sentinela interna com opção padrão desmarcada. PDF renderizado não foi verificado.
- TL: revisão de integração, achados de risco transitivo resolvidos. Veredito e limites em REVIEW.md.

Os ciclos 4 e 5 serão registrados após suas evidências.
