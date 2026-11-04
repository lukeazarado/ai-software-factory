# Tech Lead — PMO Consignado, bloco 1

Revisão independente em andamento. Não representa aprovação de merge ou publicação pública.

## Material e evidências

- Inspeção inicial de `dist/core.js`, linhas 1–33, e `PLAN.md`.
- Interface, regressões QA e diff do PR ainda não disponíveis nesta etapa.
- Nenhum teste foi executado pelo TL nesta inspeção inicial.

## Ciclo 1 — modelo e integridade

O núcleo separa funções de domínio da interface. Há validação de versão, limite de registros, tipos, datas de calendário, referências cluster/squad/projeto/marco, identificadores duplicados, dependências duplicadas, autorreferência e ciclos. A validação retorna uma cópia com campos permitidos, sem reutilizar propriedades arbitrárias importadas. A neutralização de fórmulas CSV é centralizada.

Achados em acompanhamento:

- **[MEDIA] `dist/core.js:28` — Saúde sem marcos.** Um projeto não concluído, sem marcos e com prazo futuro, recebe `No prazo`. A ausência de marcos não comprova a saúde das entregas e pode induzir leitura executiva favorável sem evidência. Correção proposta: estado explícito `Sem marcos`, tratado no painel e nos filtros. Encaminhado ao Dev.
- **[MEDIA] `dist/core.js:12` e `dist/core.js:13` — Campos previstos no plano ausentes.** O plano cita previsão própria do projeto e data real de conclusão de marco, mas o schema inicial contém apenas prazo de projeto e booleano de conclusão do marco. Correção proposta: implementar os campos ou ajustar explicitamente o escopo e as alegações de aceite com PO. Encaminhado ao Dev e Arquiteto.

Veredito do ciclo 1: **AJUSTES_OBRIGATORIOS** para a hipótese de saúde sem marcos; a discrepância de campos exige implementação ou decisão explícita de escopo. O QA independente reproduziu a inconsistência de saúde em teste automatizado. A interface e o PR ainda não foram verificados; não há parecer de homologação integral.

## Próximos ciclos — sequência operacional

2. Correções do núcleo e implementação da UI; nova execução dos testes de domínio.
3. QA real de navegador e revisão TL da integração.
4. Correções das regressões observadas e verificação de exportação/recuperação.
5. Revisão do diff real do PR, regressão final e prévia privada.

Aguardando as evidências correspondentes; a sequência não implica conclusão antecipada.

## Ciclo 2 — correção do núcleo e UI

Inspeção de `dist/core.js` pós-correção e `dist/app.js`, linhas 1–48. O núcleo agora preserva previsão/justificativa do projeto e conclusão real/justificativa do marco. A saúde `Sem marcos` substitui a alegação indevida de prazo quando não há entregas; CSV identifica a origem fictícia da demonstração.

A integração lê/valida a persistência antes de renderizar. A gravação valida a cópia candidata e chama `localStorage.setItem` antes de substituir o estado em memória. A importação valida o arquivo antes da confirmação de substituição e usa a mesma gravação. Falha de leitura não sobrescreve o conteúdo original, que pode ser baixado para recuperação. Strings interpoladas são escapadas antes de entrar em HTML; notas internas são excluídas de CSV e do relatório por padrão.

Evidência de navegador comunicada pelo orquestrador: criação de projeto de homologação em cluster/squad existentes, gravação e recarga preservando dados; saúde `Sem marcos` observada. Não realizei pessoalmente esses passos. A regressão automatizada pós-correção é responsabilidade do QA e está pendente de seu resultado final.

Veredito delimitado do incremento: **APROVADO** para continuar o ciclo de integração, sem bloqueador identificado no material estático acima. Não equivale a aprovação do PR ou da homologação completa.

Pontos abertos para ciclo 3/4:

- **[MEDIA] `dist/core.js:26` — propagação de risco atravessa marcos concluídos.** O alcance estrutural pode passar por uma entrega intermediária já concluída; usá-lo sem interromper essa cadeia pode marcar um consumidor pendente como afetado por um bloqueio que já foi superado. Correção proposta: travessia de risco que para em marcos concluídos; manter alcance estrutural separado e identificado. Encaminhado ao Dev.
- **[MEDIA] `dist/index.html` / `dist/app.js:39` — acessibilidade do dialog e erro customizado.** O dialog inicial não associa título por `aria-labelledby`; erro customizado não recebe foco nem associação explícita com os campos. Correção proposta: nome acessível do dialog e foco/descrição para erro, verificando retorno de foco após re-render. Encaminhado ao Dev; pendente QA de navegador.

## Ciclo 3 — integração, navegador e regressões

Os dois pontos do ciclo 2 foram corrigidos: a propagação operacional usa `impacts(..., {pendingOnly:true})` e para em marcos concluídos; o dialog associa título/erro, e erros customizados recebem foco. A travessia estrutural permanece separada na lista de dependências, sem prometer recálculo de cronograma.

QA independente: **21 testes aprovados**, incluindo regressão da cadeia interrompida por marco concluído e sete testes de integração em VM para carga/gravação/importação. Li as fixtures de integração: elas executam os handlers reais com DOM mínimo simulado; não constituem E2E nem validam impressão visual.

Evidência real de navegador informada pelo orquestrador:

- Cadastro de projeto com cluster/squad, gravação, recarga e persistência.
- Saúde `Sem marcos` e lista fornecedor/consumidor com organizações.
- Tentativa de dependência transitiva cíclica recusada, com seleção dos campos preservada.
- Escape fecha o dialog.
- Relatório gerado com projetos/marcos/dependências; sentinela de nota interna ausente quando a opção está desmarcada.

Limite explícito: **PDF renderizado não verificado**. O fluxo é impressão do navegador/Salvar como PDF; não há geração de arquivo PDF no backend.

Veredito do incremento: **APROVADO**, sem bloqueador remanescente identificado nas evidências acima. Ciclos 4 e 5 seguem necessários para filtros, foco, diff real e entrega final.

## Ciclo 4 — rastreabilidade e recuperação

A inspeção de `dependencyRisks`, radar e detalhe de projeto confirma que a interface agora explica a origem do risco com projeto/cluster/squad e as entregas pendentes alcançáveis. As strings seguem escapadas e a aplicação identifica que o alcance não recalcula datas automaticamente.

Novo bloqueador encontrado pelo QA e reproduzido pelo TL:

- **[ALTA] `dist/app.js:44` — backup exportado pode ultrapassar o limite de importação.** O schema aceita até 1.000 projetos com textos longos e a exportação não limita bytes, mas o importador recusa arquivos acima de 2 MiB. Reproduzi via Node um conjunto validado com 450 projetos, notas de 3.000 caracteres, objetivo e justificativa de 1.000 caracteres: o JSON indentado usado pelo backup tem **2.431.816 bytes**, acima de **2.097.152 bytes**. O arquivo pode ser exportado e não ser restaurável pela própria aplicação, criando risco de recuperação dos dados. Correção proposta: contrato único de tamanho para salvar/exportar/importar e teste de ida e volta acima de 2 MiB, mantendo um teto explícito contra arquivos excessivos. Encaminhado ao Dev/orquestrador.

Veredito em andamento: **AJUSTES_OBRIGATORIOS** até a correção de recuperação ser retestada. A aprovação do incremento anterior não cobre este achado novo.
