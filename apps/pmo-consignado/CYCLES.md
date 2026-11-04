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

## Ciclo 4 — explicação de risco e recuperação de backup

- PO/Arquitetura: explicar a origem do risco transitivo e garantir que todo backup exportado possa ser aceito de volta pelo contrato de importação.
- Dev: radar/detalhe agora mostram fornecedor e entregas afetadas com projeto/cluster/squad; janela de atualização >7 dias explícita.
- QA/TL: achado ALTA reproduzido — backup válido >2MiB era recusado. Corrigido com limite compartilhado de 32MiB e backupJSON validado antes de salvar/exportar/importar. Sem truncamento.
- QA independente: 24/24 testes, incluindo recuperação integral de 500 projetos em backup >2MiB e rejeição de arquivo acima do limite sem leitura/substituição. Testes VM do relatório cobrem filtro, opt-in de notas e texto HTML escapado.
- QA navegador: cluster e squad criados; tentativa de excluir cluster com squad foi impedida com mensagem e foco no erro. Relatório padrão não contém nota interna sentinela.
- TL independente: APROVADO no escopo verificado; aguarda diff real no ciclo 5.

## Ciclo 5 — revisão real de PR e regressão final

- PO: recorte do bloco1 atendido para homologação individual; próximos blocos dependem do checkpoint humano.
- Entrega: PR #14, branch feat/pmo-consignado-mvp. Código revisado no SHA 66209fec22acfcddfdb024a76642092ead758726, base 92ffad4b580458dcb91d404850bec2ae38fda007. Este fechamento documental não modifica código executável.
- QA: 24/24 testes reexecutados pelo orquestrador e TL; sintaxe de app.js/core.js verificada com node --check. Navegador confirmou marco concluído exige data real, preserva campos no erro e salva após correção.
- CI GitHub confirmado: PMO41845815794 e Agenda41845815697 concluídos com success no SHA de código acima.
- TL independente: diff real dos12 arquivos, conteúdo executável/testes comparado ao material local, workflow lido; APROVADO para homologação privada. Sem bloqueadores remanescentes no escopo verificado.
- Limites: PDF renderizado, layout estreito e todos os caminhos CRUD não foram integralmente exercitados; sem auditoria WCAG completa. Armazenamento local sem sincronização entre dispositivos; impactos potenciais sem reagendamento automático.
- Próxima aprovação: feedback do usuário no checkpoint5 antes dos ciclos6–10. Nenhum merge ou acesso público autorizado/executado nesta rodada.

## Bloco 2 — ciclos 6–10 (V1.2)

Autorização: o usuário pediu mais cinco rodadas e uma exploração da identidade visual/UX do Bradesco. O bloco fecha com checkpoint humano. Não são chamadas ao runner nem cinco execuções de API.

## Ciclo 6 — riscos, impedimentos e decisões

- PO: registrar riscos potenciais separados de impedimentos ativos; decisões com pergunta, opções, recomendação, responsável e data limite.
- Dev: registros vinculados a projeto, com validação, ações para criar/editar/excluir e resumo para pauta executiva. Probabilidade não é solicitada para impedimento ativo.
- Dados legados: os campos `issues` e `decisions` são opcionais no backup V1 e inicializados vazios ao carregar legado; não há migração destrutiva.

## Ciclo 7 — sinais de conflitos por squad

- Arquitetura: não inferir capacidade percentual sem disponibilidade/dedicação cadastradas.
- Dev: matriz de compromissos com projetos ativos na janela dos próximos 30 dias, marcos próximos e pares de projetos cujas janelas planejadas se sobrepõem.
- Limite explícito na interface: sinaliza concentração/conflito; não calcula utilização nem disponibilidade real.

## Ciclo 8 — simulação de atraso

- PO/Arquitetura: simular uma data de previsão para um marco pendente e propagar pelas dependências alcançáveis, preservando datas oficiais.
- Dev: propagação em DAG; em caminhos convergentes prevalece a data mais tardia entre pré-requisitos; concluídos não são reprogramados; filtro visual mantém o recorte de projetos sem cortar a propagação transitiva.
- Testes verificam a saída da simulação e a não mutação do grafo/datas oficiais.

## Ciclo 9 — exploração de identidade visual e UX

- Referência solicitada: página inicial oficial Bradesco (`https://banco.bradesco/html/classic/index.shtm`), inspecionada no navegador.
- Decisão: usar vermelho/crimson, bordô e neutros brancos/cinzas em hierarquia própria de produto PMO. Não copiar marca, logotipo, banners ou padrões de autenticação financeira.
- Hierarquia aplicada para navegação e ações; severidade de risco continua com sinalização semântica distinta. Foco de teclado usa contorno visível e cores com contraste reforçado.
- Limite: inspiração visual avaliada, não uma auditoria WCAG ou teste formal com usuários.

## Ciclo 10 — regressão, integração e preparação para homologação

- Dev: versão visual V1.2; testes de armazenamento V1/V1.1 ajustados para incluir o novo módulo executivo; relatório inclui riscos/decisões aplicáveis sem observações internas por padrão.
- QA local inicial: 43 aprovados; revisão independente sinalizou classificação indevida de períodos sequenciais como simultâneos. Correção registrada abaixo.
- Navegador: preview local confirmou fluxo de cadastro/edição de risco e decisão, persistência após recarregar, tipo impedimento, matriz de squads, simulação com dependências transitivas e ausência de alteração às datas oficiais. O modal do relatório foi aberto; a renderização visual/PDF ainda não foi confirmada.
- TL independente: o achado do diff inicial foi corrigido; revisão do SHA `8481b7922bddf84a678f9c3c1bfc7a0801e3e653` confirmou a correção e não encontrou novos bloqueadores. APROVADO para homologação privada.
- QA automatizado atualizado: `node --test --test-reporter=spec tests/*.test.mjs` — 44 aprovados, 0 falhas; `node --check` de `app.js`, `core.js` e `executive.js` passou.
- CI no SHA atualizado do PR: PMO `41891834670` e Agenda `41891834754`, ambos success.
- Próxima aprovação: feedback humano neste checkpoint de cinco ciclos. Sem merge; site deve continuar privado.
