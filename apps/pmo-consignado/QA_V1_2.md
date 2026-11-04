# QA — PMO Consignado V1.2

## Evidência automatizada local

Comando executado na raiz do app:

```text
node --test --test-reporter=spec tests/*.test.mjs
```

**44 testes passaram; 0 falhas.** Incluem regressões V1 e V1.1, carregamento de backup antigo, validação e referências executivas, janelas sobrepostas e sequenciais, propagação de atraso por dependências convergentes, recorte de projetos e não mutação das datas oficiais.

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

## Limites da evidência

Não houve verificação completa em viewport móvel, automação E2E, teste de leitor de tela ou auditoria WCAG. O site conserva armazenamento local por navegador, sem sincronização. As ações manuais ocorreram apenas no preview local; não foram feitas nos dados da publicação privada.

## Correção após revisão independente

O TL detectou que períodos sequenciais sem sobreposição eram rotulados como simultâneos. A regra foi corrigida: apenas pares realmente sobrepostos recebem o sinal de sobreposição; múltiplos projetos sem pares sobrepostos são identificados como “Janelas distintas”. Foi adicionado teste de regressão. A classificação corrigida foi coberta por teste automatizado; não foi repetida manualmente no navegador após esse ajuste de rótulo.
