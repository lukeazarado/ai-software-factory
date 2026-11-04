# Órbita PMO — v1.1 experimental

Branch exclusiva: `explore/chat-pmo-ux-20261104`. A versão de produção/da main não foi alterada. Este é um incremento de UX e consultas, não um ciclo executado por agentes Python independentes.

## Escopo entregue
1. **Clusters e squads:** cards passam a respeitar cluster e squad selecionados, a busca textual por cluster/squad/projetos do recorte e as contagens de projetos filtrados. O status é aplicado aos projetos contados; clusters sem projetos correspondentes ainda podem ser exibidos quando selecionados explicitamente.
2. **Dependências:** busca textual própria por nome de marco fornecedor ou consumidor, combinada com os filtros globais; contagem de vínculos encontrados.
3. **Cronograma:** seletor “Por projetos” / “Por marcos e entregas”. Marcos usam data real quando concluídos e previsão quando pendentes, com indicação de projeto/squad e datas.
4. **Destaques semanais:** painel executivo lista marcos concluídos de segunda a domingo da semana corrente, conforme `actual`, respeitando os filtros globais. Não infere conclusões a partir de previsões.

## Critérios de aceite
- Filtrar cluster A mostra somente cards do cluster A; filtrar squad B mostra sua organização, e limpar filtros restaura a visão geral.
- Buscar um nome de marco em Dependências retorna vínculos onde ele é fornecedor **ou** consumidor; busca vazia restaura a lista.
- Alternar a subvisão de cronograma não altera dados e respeita filtros de projeto.
- Marco concluído com data real nesta semana aparece no destaque; marco pendente e marco concluído fora da semana não aparecem.
- A experiência permanece operável por teclado e em largura de 320/375 px; validação real pendente.

## Limites e riscos
- O modelo atual não exige `actual` para marcos `done=true` importados. A lista semanal omite esses registros, sem inventar datas. A correção do schema deve considerar backups legados e testes de migração.
- Nenhuma suíte Node, E2E ou teste de navegador foi executado **nesta conversa**; os arquivos foram inspecionados e versionados via GitHub.
- Sem sincronização ou backend; sem publicação/merge.
- Revisão TL: `NAO_VERIFICADO` até CI, inspeção do diff e homologação UX.

## Próximo checkpoint
Executar `node --check dist/app.js`, `node --check dist/core.js` e `node --test tests/*.test.mjs` na branch, verificar visualmente em Codespaces e obter parecer TL sobre diff e riscos. Corrigir regressões antes de propor merge.
