# PMO Consignado — plano do bloco 1

## Produto e evidências

O usuário precisa acompanhar projetos, datas e interdependências da tribo de Consignado, organizada em clusters (subáreas) e squads. Será o único operador. A diretoria receberá relatórios exportados. Esta especificação deriva da conversa; não representa pesquisa com usuários ou validação de usabilidade.

Objetivo principal: identificar qual entrega pode atrasar outra e localizar a responsabilidade organizacional pelo desbloqueio.

## Escopo MVP

- Cadastro de clusters e squads, com relação obrigatória squad → cluster.
- Projetos com título, objetivo, responsável, prioridade, squad responsável, início, prazo planejado, previsão e notas internas.
- Marcos por projeto com título, data planejada, previsão e conclusão real opcional.
- Dependências direcionadas entre marcos: fornecedor → consumidor. Uma aresta significa que a entrega do fornecedor é necessária para o marco consumidor.
- Painel executivo, filtros organizacionais, cronograma e lista legível de dependências.
- Persistência local, backup JSON validado, exportação CSV protegida contra fórmulas e relatório de impressão/PDF.
- Dados demonstrativos claramente identificados e opção de começar sem eles.

Fora deste bloco: contas multiusuário, servidor, sincronização, integração Jira/Linear, capacidade quantitativa dos times e cálculo automático de novo cronograma.

## Modelo mínimo

| Entidade | Relações e regras |
| --- | --- |
| Cluster | Tem squads; não pode ser excluído enquanto possuir squads. |
| Squad | Pertence a um cluster; não pode ser excluída enquanto possuir projetos. |
| Projeto | Tem uma squad responsável e vários marcos; responsável é um texto, não uma identidade/autorização. |
| Marco | Pertence a um projeto; datas devem ser datas de calendário válidas. |
| Dependência | Liga dois marcos existentes, sem autorreferência, duplicidade ou ciclo. |

Dependências entre clusters ou squads são derivadas das entregas vinculadas. A interface deve mostrar explicitamente as organizações do fornecedor e consumidor. Atribuir um projeto a um cluster não significa que ele depende de todos os projetos desse cluster. Participação de múltiplas squads pode evoluir depois sem comprometer a responsabilidade principal.

## Arquitetura

HTML semântico + CSS responsivo + JavaScript em módulos, sem serviços externos ou bibliotecas. `core.js` contém validação, datas, grafo e cálculos puros; `app.js` mantém estado, armazenamento e interface. `localStorage` armazena somente os dados do operador naquele navegador/origem. A camada de gravação informa falha e não apresenta como salvo um estado que não foi persistido.

Importações devem ser validadas integralmente antes de substituir o estado. Exibir confirmação para substituir dados existentes. Backup recomendado antes da importação. Não sobrescrever silenciosamente conteúdo inválido já armazenado com os dados de demonstração.

Conteúdo informado pelo usuário deve ser inserido com APIs de texto. Relatórios e CSV devem preservar a privacidade das notas internas por padrão. Exportar CSV com escape de aspas/quebras e neutralização de prefixos de fórmula.

## Cinco incrementos e critérios de passagem

Cada ciclo é uma rodada de escopo → desenho → implementação → QA → parecer TL. A tabela descreve a ordem de incremento; só registrar um ciclo como concluído depois das evidências correspondentes.

| Ciclo | Incremento | Critérios observáveis de aceite |
| --- | --- | --- |
| 1 | Estrutura e portfólio | Criar/editar/excluir clusters e squads com integridade referencial; criar e editar projeto; campos obrigatórios mantêm os valores digitados ao falhar; recarregar preserva os cadastros. |
| 2 | Marcos e dependências | Registrar marco com datas válidas; conectar entregas de projetos distintos; mostrar fornecedor e consumidor com suas squads/clusters; rejeitar autorreferência, duplicata, ciclo direto e ciclo transitivo; avisar impacto ao excluir marco com vínculos. |
| 3 | Controle executivo | Exibir indicadores com denominadores claros; filtrar por cluster/squad/projeto/situação sem números contraditórios; distinguir atraso próprio, risco de dependência e falta de atualização; apontar entregas afetadas sem alterar datas automaticamente. |
| 4 | Exportação e recuperação | JSON faz ida e volta preservando dados; importação inválida/cíclica/com referências inexistentes é recusada sem modificar dados anteriores; CSV abre com conteúdo textual seguro; relatório respeita filtros e exclui notas internas; identifica data de emissão e demonstração. |
| 5 | Homologação e correções | Fluxos principais utilizáveis por teclado; rótulos e erros associados; dialog fecha por Escape e devolve foco; layout estreito sem cortar ações; armazenamento indisponível gera aviso visível; regressões do core passam; TL revisa o diff real e documenta limites. |

## Semântica de controle

- Datas são calendários locais, sem converter `YYYY-MM-DD` em instantes UTC para comparar ou mostrar.
- Marco concluído não permanece em atraso operacional, mas seu desvio histórico pode ser apresentado.
- Dependência em risco: fornecedor pendente cuja previsão ultrapassa a data necessária do consumidor; deixar o critério legível. Fornecedor pendente já vencido também requer atenção.
- Impacto transitivo é alcance do grafo: possibilidade de comprometimento, não comprovação de atraso ou cálculo de caminho crítico.
- Projetos sem marcos devem ter estado explícito; ausência de marcos não comprova saúde.
- Atualização antiga deve ter janela explícita (proposta: 14 dias) e não ser confundida com atraso.
- Conclusão/progresso por contagem de marcos é aproximada e deve indicar essa base; não usar percentuais de esforço sem dados.

## Riscos e limites

1. Perda do navegador/origem apaga acesso ao armazenamento: backup JSON e orientação visível são necessários.
2. Abrir a aplicação em outro dispositivo não sincroniza dados.
3. Impressão permite salvar PDF pelo navegador; não prometer PDF binário gerado ou exportação PPTX.
4. Relacionamentos complexos podem ficar ilegíveis: manter a lista de dependências como alternativa ao mapa.
5. Dados demo precisam ser distinguíveis de dados reais também nas exportações.
6. Revisões técnicas e testes não substituem a homologação do operador; não declarar conformidade WCAG completa sem auditoria adequada.

## Checkpoint do ciclo 5

Apresentar URL privada, PR, evidências reais de QA, parecer independente e limitações. Pedir ao usuário avaliar: terminologia de clusters/squads; utilidade do painel e relatório para a diretoria; prioridade do próximo bloco (capacidade dos times, riscos/decisões ou cenários de atraso). Não fazer merge nem publicar acesso público automaticamente.
