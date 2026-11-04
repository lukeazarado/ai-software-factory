# Exploração UX — referência Bradesco

Referência indicada pelo usuário: [site Bradesco](https://banco.bradesco/html/classic/index.shtm), inspecionado em 4 de novembro de 2026.

## Padrões observados e tradução para o PMO

| Referência cromática/visual | Tradução no Órbita |
| --- | --- |
| Vermelho com uso de alto destaque | Navegação ativa e ações prioritárias usam crimson/bordô. |
| Branco e cinzas em áreas de conteúdo | Cartões e tabelas mantêm superfícies neutras para leitura de dados. |
| Destaques agrupados por função | Riscos, conflitos e decisões ficam em áreas próprias com rótulos diretos. |

O PMO não reutiliza logotipo, imagens, textos, formulários bancários ou identidade de navegação do Bradesco. A paleta é uma referência de cor, não uma tentativa de reproduzir a instituição.

## Diretrizes aplicadas

- Vermelho reforça navegação e prioridade; não substitui os rótulos de status.
- Severidade de risco, sucesso e pendência preservam significados diferentes.
- Foco de teclado recebe contorno visível e contraste escurecido.
- A interface declara os limites dos sinais: sobreposição de projetos não prova falta de capacidade; atraso simulado não muda datas oficiais.

## Validação pendente

A primeira exploração foi feita por inspeção visual da referência e do preview. Não houve entrevistas, teste moderado, medição formal de contraste/WCAG ou validação mobile completa.

## Revisão UX retrospectiva da V1.2

A revisão aplicou a skill versionada `projetar-ux` aos fluxos de riscos/decisões, conflitos, simulação e navegação responsiva. Fatos de implementação foram separados de hipóteses; não foram inventados dados de pesquisa.

### Achados priorizados

| Severidade UX | Evidência | Recomendação/ação |
| --- | --- | --- |
| 2 — atrito moderado | CSS mobile usava oito rotas numa faixa horizontal sem affordance clara para conteúdo fora da tela. | Trocar por grade visível de duas colunas, alvos de 48 px e nomes que quebram em linhas. Implementado; reflow visual em 320–390 px ainda não testado. |
| 2 — atrito moderado | Ao mudar a fonte/data da simulação, o conteúdo visual é recalculado, mas não há mensagem específica para tecnologia assistiva. | Região persistente `role=status`, `aria-live=polite`, `aria-atomic=true` anuncia fonte, data e total afetado. Implementada e coberta por teste VM; leitor de tela não testado. |
| 1 — conteúdo | O histórico resolvido oferece ação Editar sem indicar isso no texto da seção. | Esclarecer que registros encerrados permanecem disponíveis e podem ser editados. Implementado. |

### Convergência Arquiteto + UX

O Arquiteto concordou com as duas correções moderadas e com o ajuste menor, sem divergência ou arbitragem do PO. Não foi usado agente pago/API nem invocado `factory/runner.py --enable-ux`; a skill foi aplicada em revisor UX dedicado nesta conversa. Esse trabalho corrige a lacuna de revisão, mas a etapa UX não ocorreu antes da implementação original da V1.2.

### Critérios de aceite e plano de validação

- Em 320–390 px, acessar as oito rotas sem scroll horizontal, com rótulos completos, alvos de no mínimo 44 px e foco visível.
- Ao alterar fornecedor ou data, tecnologia assistiva anuncia uma vez marco/data/total no recorte; o foco continua no controle e a tabela não é lida inteira.
- Histórico esclarece que registros resolvidos podem ser editados.
- Verificar reflow/zoom, teclado e leitor de tela (NVDA ou VoiceOver) antes de declarar conformidade WCAG 2.2 AA.

Os testes desta entrega cobrem o contrato de marcação e a atualização textual em VM, não a apresentação visual em dispositivo nem o anúncio real por tecnologia assistiva. A validação prática ainda depende do checkpoint de homologação.
