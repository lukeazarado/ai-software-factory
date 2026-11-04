# Órbita — PMO Consignado v1.1

Portal individual da tribo de Consignado: clusters, squads, projetos, marcos e dependências entre entregas. Aplicação estática sem serviços externos. Dados demonstrativos são fictícios.

Na V1.1, os filtros de estrutura respeitam cluster/squad/busca, as dependências têm pesquisa por marco e o cronograma separa Projetos, Marcos e entregas e Conquistas semanais. As conclusões da semana usam exclusivamente a data real, de segunda a domingo, e também aparecem no relatório executivo. Detalhes em `V1_1.md`, `QA_V1_1.md` e `REVIEW_V1_1.md`. Esta manutenção precede os ciclos 6–10.

## Executar

Sirva esta pasta por HTTP com um servidor estático e abra `dist/`. Os módulos JavaScript não devem ser abertos por `file://`.

## Dados e exportação

Os cadastros ficam no armazenamento local do navegador, vinculados à origem do site. Não há sincronização entre dispositivos. Exporte backups JSON regularmente; o CSV é uma visão tabular, não um backup completo. O relatório executivo usa a impressão do navegador, que permite salvar em PDF. Notas internas ficam fora do relatório padrão e do CSV.

Dependências seguem a direção fornecedor → consumidor, entre marcos. Cluster e squad responsáveis são derivados dos projetos de cada entrega. Alcance transitivo representa impacto potencial; não é cálculo de caminho crítico nem altera prazos automaticamente.

## Verificação

Na raiz deste aplicativo: `node --test tests/*.test.mjs`.

Consulte `PLAN.md` para escopo e critérios, `REVIEW.md` para revisão independente e `CYCLES.md` para as evidências de execução. Esta entrega não modifica o runner da fábrica nem faz merge automático.

## Homologação

1. Criar cluster, squad e projeto; recarregar e conferir persistência.
2. Criar dois marcos e vincular fornecedor/consumidor; testar a rejeição de um ciclo.
3. Conferir alertas e filtros por cluster/squad.
4. Exportar JSON/CSV e abrir o relatório executivo; conferir a ausência de notas internas.
5. Importar backup válido e conferir recuperação; tentar um arquivo inválido e verificar que os cadastros anteriores permanecem.

Não foram executadas entrevistas com usuários nem uma auditoria completa de acessibilidade. Homologação humana permanece necessária.
