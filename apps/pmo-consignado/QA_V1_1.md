# QA independente — PMO Consignado v1.1

Esta manutenção implementa os quatro ajustes solicitados antes do próximo bloco de ciclos. Não representa os ciclos 6–10.

## Resultado observado

Comando: `node --test tests/*.test.mjs` a partir desta pasta.

**37 testes aprovados; 0 falhas.** São 24 testes de regressão v1.0 e 13 casos novos em `tests/v1_1.test.mjs`. Nenhuma dependência adicional foi instalada para executar a suíte.

| Ajuste | Evidência executada |
| --- | --- |
| Organização | Filtros de cluster, squad e nomes combinados; cluster sem squads e squad sem projetos permanecem localizáveis; seleção incompatível retorna vazio no core e é limpa ao reconstruir as opções na integração. Situação de projeto é ignorada na estrutura, fica oculta/desabilitada e volta preservada nas outras visões. |
| Busca | Projeto/responsável, cluster/squad e nomes dos dois marcos de uma dependência aceitam caixa e acentos diferentes, com espaços periféricos. Ex.: `originacao`, `INTEGRACOES`, `JOAO` e `API DISPONIVEL`. Texto armazenado permanece intacto. |
| Dependências | O recorte por projetos inclui vínculo cujo fornecedor **ou** consumidor pertença ao recorte; a busca pelo nome de um dos marcos se combina com esse recorte. Busca não traz vínculo de projetos fora do escopo. |
| Cronograma | Ordenação por data planejada, previsão ou conclusão real respeita projetos filtrados; registros sem data real ficam ao final; os dados originais não são reordenados nem alterados. |
| Conquistas semanais | Período de segunda a domingo inclusivo; somente marcos concluídos com `actual` válida dentro da semana contam. Datas planejadas/previsões dentro da semana não incluem conclusão de outra semana. Marcos pendentes e concluídos legados sem data real não contam. Agrupamento por squad/cluster e filtros de projetos verificados. |
| Calendário | Domingo pertence à semana que termina naquele dia; segunda seguinte inicia outra. Foram executadas fronteiras de ano, fevereiro bissexto e transições DST em UTC, São Paulo, Nova York e Auckland. Extremos de referência 1900/2200 e navegação fora da faixa foram testados. |
| Relatório | Integração executa handlers reais: semana selecionada sobrevive à navegação e o HTML executivo contém o mesmo intervalo e somente as conquistas dos projetos do recorte. Regressão mantém exclusão padrão de notas internas, opt-in explícito e escape de HTML. |
| Compatibilidade | `VERSION` permanece 1 e o carregamento continua usando `orbita-pmo-v1`. Backups antigos sem campos opcionais são normalizados; conclusão legada sem `actual` não recebe data inventada. Testes anteriores de corrupção, quota, importação e backup >2 MiB continuam passando. |

## Achados e correções verificadas

- A primeira implementação fazia comparação sem diferenciar caixa, mas exigia os acentos. Os três testes de busca sem acento falharam inicialmente. O critério foi confirmado pelo orquestrador; o Dev centralizou a normalização e os testes passaram.
- O Dev adicionou proteção à navegação de semanas nos extremos da faixa de datas. A suíte verifica que o passo recusado não altera a semana nem lança erro ao renderizar.

Não foram encontrados bloqueadores adicionais no material efetivamente testado.

## Limites

Os testes de integração executam o código real de `app.js` em Node VM com DOM/armazenamento mínimos simulados. O fixture reproduz seleção de opções apenas para verificar coerência de filtros; ele não substitui navegador real. Esta evidência não comprova layout, foco/cursor de busca, semântica de teclado, diálogos nativos, impressão/PDF renderizado ou download físico. O orquestrador conduz essas verificações no navegador; a homologação final é do usuário.
