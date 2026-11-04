# Tech Lead — PMO Consignado v1.1

Manutenção dos quatro ajustes solicitados, antes dos ciclos 6–10. Esta revisão não contabiliza um novo bloco de cinco ciclos.

## Estado da revisão

**APROVADO** tecnicamente para homologação privada da V1.1 no PR #15, head `e65d34bc69c7dd15bfe04d9207737bb27487f77f`, base `c9b0de1597542e159bd6c46d13c899f5eb11e487`. Diff real e os sete arquivos conferidos; 37 testes passaram na reexecução independente. Nenhum bloqueador remanescente encontrado no material verificado. Esta recomendação não aprova formalmente o PR nem autoriza merge ou publicação pública.

## Diagnóstico da base v1.0

Inspecionei `dist/app.js` e `dist/core.js` antes das alterações.

- **[MEDIA] `dist/app.js:23–24` — filtros visíveis sem efeito organizacional.** `render` calcula os projetos filtrados, mas chama `organization()` sem o recorte; a função percorre todos os clusters/squads e contabiliza todos os projetos. A tela sugere filtro aplicado quando mantém resultados globais. Corrigir cluster/squad e busca com semântica explícita; filtro de situação deve ser ocultado/desconsiderado nessa visão para não excluir estruturas sem projeto.
- **[MEDIA] `dist/app.js:21` — cronograma sem subvisões.** Projetos e marcos aparecem no mesmo fluxo; falta a subaba Marcos/Entregas solicitada. Nova navegação deve preservar os filtros e indicar o modo ativo.
- **[MEDIA] `dist/app.js:22` — vocabulário inconsistente.** A visão de dependências alterna entrega/marco; padronizar os rótulos pedidos pelo usuário em Marcos, mantendo a direção fornecedor → consumidor.
- **[MEDIA] `dist/app.js:20,46` — ausência de destaques semanais reais.** Painel e relatório só destacam previsões/pendências. Conclusão semanal precisa usar `done === true` e `actual` válida; não pode usar data prevista, data planejada ou data de atualização como substituto.

Reprodução em navegador comunicada pelo orquestrador: selecionar cluster Plataforma restringiu as opções de squad para Integrações, mas a visão organizacional manteve quatro clusters. Confirma que o problema de recorte é observável na interface, além da evidência estática.

## Critérios de revisão da v1.1

1. Organização: selecionar cluster e squad restringe a estrutura exibida, incluindo organizações sem projetos quando pertinente. Busca organizacional declara os campos pesquisados. Situação de projeto é oculta/desconsiderada ali e seu valor volta a ter efeito nas visões de projeto.
2. Filtros: re-renderização preserva seleção e foco utilizável; limpar filtros recupera a estrutura completa; não há incompatibilidade cluster/squad após seleção ou importação.
3. Dependências: busca textual por nomes dos marcos fornecedor/consumidor, sem exigir correspondência no nome do projeto/responsável. Navegação, títulos, ações e descrições deixam a semântica de Marcos clara, sem alterar o grafo salvo ou inverter suas arestas.
4. Cronograma: subvisões Projetos e Marcos/Entregas; ambas respeitam o recorte de projetos. Mudança de subvisão não altera os dados.
5. Semana: intervalo local de segunda-feira a domingo, inclusive; domingo pertence à semana que termina nesse domingo. Seleção por data, anterior/atual/próxima sem deslocamento indevido em fuso/DST.
6. Entregas reais: somente marcos concluídos com data real válida no intervalo. Concluídos legados sem `actual` não entram como entrega da semana; devem permanecer legíveis como data real não informada. Nenhuma data é inventada ou gravada automaticamente.
7. Destaques coerentes no painel, cronograma e relatório; período e filtros identificados, notas internas continuam fora do relatório padrão e texto de usuário segue escapado.
8. Compatibilidade: `VERSION = 1`, chave `orbita-pmo-v1` e leitura/backup legado mantidos; novas funções são de apresentação/cálculo, sem migração destrutiva ou substituição do armazenamento.

## Evidências pendentes

- Testes reais de semana, fusos/DST, filtros de estrutura, datas reais e dados legados.
- Regressão de persistência/importação/exportação e segurança de conteúdo.
- Navegador para filtros, foco, subabas e destaques.
- Diff real do PR e correspondência do código testado com seu head.

Parecer final será registrado após essas evidências, com bloqueadores separados de melhorias opcionais e limites explícitos.

## Inspeção intermediária da implementação

Novos helpers puros implementam os recortes de projetos, estrutura e dependências, o intervalo semanal e a seleção de conclusões reais. `VERSION = 1` e chave de armazenamento foram mantidas. `weeklyDeliveries` exige conclusão e `actual` válida no intervalo inclusivo; o aviso de legados sem data se refere corretamente ao recorte inteiro, sem atribuí-los a uma semana. As novas strings de usuário na tabela/relatório seguem escapadas.

Os controles recriados do cronograma e da semana receberam IDs estáveis, permitindo que `renderKeepingFocus` recupere o elemento após a troca da subvisão/semana. Ainda requer comprovação em navegador.

Achados encaminhados ao Dev antes do congelamento:

- **[MEDIA] `dist/app.js`, handler `data-week-step` — navegação pode invalidar o estado semanal.** Selecionar o mínimo aceito `1900-01-01` e ir à semana anterior produz referência de 1899; o estado é alterado antes de `weekBounds` recusar a data. O próximo render/relatório lança até corrigir o estado. Extremo superior tem caso equivalente. Proposta: verificar a próxima referência antes de atualizar o estado e impedir navegação além do intervalo, com mensagem legível.
- **[MEDIA] `dist/app.js`, `report` — filtro de marcos oculto afeta outra visão.** A busca específica de dependências permanece preenchida ao sair da aba e é aplicada ao relatório de outra visão, apesar de não estar visível no recorte atual. Proposta: aplicar essa busca ao relatório somente quando a origem for Dependências e alinhar a descrição dos filtros; preservar seu valor para retorno à aba.

Os achados são verificações estáticas/reprodução lógica; não representam resultados de navegador já executados pelo TL.

## Reavaliação independente após correções

Inspecionados `dist/app.js`, `dist/core.js`, `dist/index.html`, `dist/styles.css` e os testes novos. A navegação semanal agora calcula a próxima referência e verifica `isDate` antes de atualizar `selectedWeek`; botões nos extremos são desabilitados. O relatório aplica a busca específica de marcos somente quando aberto em Dependências e identifica “Não aplicado nesta visão” nos demais contextos. Esses dois achados intermediários estão resolvidos no código local verificado.

Os recortes organizacionais são calculados por cluster/squad/nome, preservando estruturas sem projetos. A situação de projeto fica oculta e desabilitada ali; a seleção permanece preservada para as outras visões. Busca organizacional e busca de projeto possuem estados separados. A pesquisa específica por marco é externa à área recriada; os controles recriados do cronograma/semana têm IDs estáveis para recuperar o foco.

O núcleo mantém `VERSION = 1` e a chave de armazenamento `orbita-pmo-v1`; não há migração, substituição automática dos dados existentes nem invenção de datas reais. As novas saídas de texto seguem escapadas. Alterações de demonstração só atuam quando não há dados persistidos.

Executei `node --test tests/*.test.mjs` nesta revisão: **37 testes, 37 aprovados, 0 falhas**. Os testes incluem 24 regressões V1 e 13 casos novos de filtros, calendário, semana, dados legados e integração VM. Não constituem E2E ou PDF renderizado.

Não encontrei novo bloqueador na inspeção local. O parecer final do PR está documentado a seguir.

## Revisão final do PR #15

### Fonte e correspondência

- Head revisado: `e65d34bc69c7dd15bfe04d9207737bb27487f77f`.
- Base: `c9b0de1597542e159bd6c46d13c899f5eb11e487` (`main`, após a integração da V1).
- Li a coleção real de arquivos/diffs do PR via GitHub: quatro arquivos executáveis modificados (`app.js`, `core.js`, `index.html`, `styles.css`) e três arquivos adicionados (`V1_1.md`, `QA_V1_1.md`, `tests/v1_1.test.mjs`). Os patches contêm todas as linhas adicionadas/removidas informadas pela API; não há diff truncado pendente.
- Os sete blobs do PR coincidem com os hashes Git dos arquivos locais efetivamente inspecionados/testados. A base dos quatro executáveis do checkout local também coincide com a base GitHub V1.
- Checklist seguido: `docs/TECH_LEAD.md` do repositório, lido no SHA da base.

### Evidência de navegador comunicada pelo orquestrador

Não executei pessoalmente estes passos; foram realizados no navegador real pelo orquestrador:

- Filtro Plataforma exibe somente esse cluster; estrutura de QA sem projetos permanece visível. Busca `originacao` encontra Originação.
- Pesquisa por marco consumidor `consulta` exibe um vínculo, com foco de digitação preservado.
- Cronograma apresenta as três subvisões, marcadores de datas planejada/prevista/real e lista textual correspondente.
- Semana de 2 a 8 de novembro apresenta uma conclusão demonstrativa; escolher domingo 8 normaliza para segunda 2. Agrupamento por cluster apresenta Plataforma.
- Semana anterior (26 de outubro a 1 de novembro) apresenta zero conclusões e mantém foco em `week-previous`.
- Navegar para o painel e gerar relatório preserva esse período e contagem. A nota interna demonstrativa não aparece; a busca de marco oculta não restringe o relatório do painel, cuja descrição informa que ela não está aplicada.

### Checklist e veredito

| Área | Parecer |
| --- | --- |
| Escopo/correção | Os quatro ajustes solicitados estão implementados; organização e dados de entregas possuem semântica explícita. |
| Arquitetura | Mantém HTML/CSS/JS e funções de domínio puras, sem dependências adicionais. |
| Segurança/dados | Conteúdo de usuário escapado; schema/chave preservados; nenhuma data real inventada ou migração destrutiva. |
| Testes | Reexecutei 37/37; regressões de persistência, quota, backup, conteúdo e novos filtros/calendário passaram. |
| Operação | Origem e armazenamento individual preservados; V1 pode ser restaurada por versão de código sem migração de dados. |

Os achados médios registrados na análise intermediária foram corrigidos. Não há bloqueador ou ajuste obrigatório remanescente no escopo verificado. Não proponho refatorações apenas estéticas para esta manutenção.

Limites: PDF visual, download físico, layout estreito completo e auditoria de acessibilidade não foram verificados pelo TL. A evidência de integração usa VM/DOM mínimo; não representa E2E. Em consulta final à API GitHub, confirmei que os CIs PMO `41884526330` e Agenda `41884526169` concluíram com `success` no head revisado.

**VEREDITO: APROVADO para homologação privada**, condicionado à preservação do código revisado. Homologação e decisão de merge continuam humanas. Não publiquei comentário/review formal, não fiz merge e não executei deploy.
