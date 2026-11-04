# QA — PMO Consignado V1.2

## Evidência automatizada local

Comando executado na raiz do app:

```text
node --test --test-reporter=spec tests/*.test.mjs
```

**47 testes passaram; 0 falhas.** Incluem regressões V1 e V1.1, carregamento de backup antigo, validação e referências executivas, janelas sobrepostas e sequenciais, propagação de atraso por dependências convergentes, anúncio textual do cenário e não mutação das datas oficiais.

Verificações de sintaxe executadas:

```text
node --check dist/app.js
node --check dist/core.js
node --check dist/executive.js
```

As três passaram sem saída de erro.

## Verificação manual no preview local

- Criar e salvar risco e decisão; ambos aparecem no painel. A informação sobrevive a recarregar a página.
- Trocar risco potencial para impedimento ativo remove o campo de probabilidade.
- Matriz de squads informa janela de 30 dias, projetos e marcos sem apresentar percentual inventado de utilização.
- Simulação de atraso em marco pendente mostra impacto direto e transitivo, inclusive em dependência entre squads; a interface informa que datas oficiais não são alteradas.
- Modal de relatório abriu e manteve a opção de observações internas desmarcada. A impressão nativa foi solicitada, mas o PDF/renderização final não foi visualmente conferido.
- Teste VM confirma que mudança da data simulada preenche a região persistente `role=status` depois do rerender. Teste estático confirma a região fora de `#view` e CSS da grade mobile em duas colunas.

## Limites da evidência

Não houve verificação completa em viewport móvel, automação E2E, teste com leitor de tela ou auditoria WCAG. Os novos critérios de 320–390 px e anúncio no leitor de tela precisam de verificação prática. O site conserva armazenamento local por navegador, sem sincronização. As ações manuais ocorreram apenas no preview local; não foram feitas nos dados da publicação privada.

## Correção após revisão independente

O TL detectou que períodos sequenciais sem sobreposição eram rotulados como simultâneos. A regra foi corrigida: apenas pares realmente sobrepostos recebem o sinal de sobreposição; múltiplos projetos sem pares sobrepostos são identificados como “Janelas distintas”. Foi adicionado teste de regressão. A classificação corrigida foi coberta por teste automatizado; não foi repetida manualmente no navegador após esse ajuste de rótulo.

## Correção após revisão UX retrospectiva

A revisão da skill `projetar-ux` e a convergência com o Arquiteto apontaram navegação móvel sem indicação clara de rotas fora da faixa e falta de anúncio próprio quando a simulação muda. A navegação mobile agora usa grade de duas colunas, sem scroll horizontal; mudanças no cenário atualizam uma região persistente `aria-live`; histórico esclarece que registros resolvidos continuam editáveis. Testes automatizados cobrem o anúncio e os seletores/atributos previstos; viewport físico e leitor de tela permanecem pendentes.

## Revisão independente do PR #16

No SHA `2516efb243f96c1d04383db4c126c34b3099057a`, QA independente reexecutou 47/47 testes, checks de sintaxe e `git diff --check`; tudo passou. Confirmou no diff a região de status, handlers, grade e rótulos mobile, sem bloqueadores de QA.

CI do PMO `41894630788` e da Agenda `41894630867`: success. Não foram testados viewport físico, teclado completo, leitor de tela ou conformidade WCAG; os testes verificam VM, código e seletores, não validação com tecnologia assistiva.
