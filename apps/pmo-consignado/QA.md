# QA independente — PMO Consignado

## Evidências por área funcional

| Área | Evidência automatizada disponível | Verificação de interface |
| --- | --- | --- |
| 1 — Estrutura e portfólio | Schema, integridade cluster/squad/projeto, campos obrigatórios, prioridades/status, datas válidas e início/fim; armazenamento válido recarregado sem sobrescrita | Orquestrador confirmou projeto criado e persistência após recarregar no navegador. CRUD completo ainda depende da homologação. |
| 2 — Marcos e dependências | Referências de marcos, duplicatas, autorreferência, ciclos diretos/transitivos e alcance transitivo do grafo | Pendente: criação/exclusão e visibilidade organizacional |
| 3 — Controle executivo | Saúde de concluído/atrasado/pausado, risco direto e transitivo de dependência; regressão interrompe risco em marco concluído | Falha “sem marcos → No prazo” corrigida e retestada; navegador confirmado pelo orquestrador. Janela de atualização implementada: mais de 7 dias. |
| 4 — Exportação e recuperação | JSON ida/volta e validação sem mutação; referências inválidas recusadas; CSV escapa aspas e neutraliza fórmulas; notas internas excluídas. Integração do código real em VM: relatório respeita filtro e opt-in de notas, identifica demo e escapa texto HTML; importação inválida/cancelada/confirmada e >32MiB; load corrupto/bloqueado sem sobrescrita; quota preserva estado anterior. | Pendente nesta revisão: relatório/PDF renderizado e download físico. |
| 5 — Regressão | Datas em quatro fusos e transições DST; previsão/justificativa e conclusão real preservadas; suíte final: 24/24 testes aprovados | Pendente nesta revisão: teclado, foco de diálogos, estreito no navegador. |

Comando reproduzível: `node --test tests/*.test.mjs` a partir desta pasta. Resultado observado: 24 testes, 24 aprovados, 0 falhas. Os testes importam `dist/core.js` por data URL para não depender de package.json ou pacotes externos.

`storage.test.mjs` executa o código real de `app.js` em Node VM com armazenamento e DOM mínimos simulados. Ele verifica ordem e integridade das gravações e handlers de importação; não emula layout, semântica de controles, downloads físicos, foco nem impressão. Esses testes não representam E2E, conformidade WCAG, abertura em Excel, PDF renderizado nem uso em produção.

## Achados corrigidos

- Saúde indevidamente positiva sem marcos: o core retorna “Sem marcos” em vez de “No prazo”. Teste de regressão passa.
- Risco transitivo atravessando entrega já concluída (achado do TL): o alcance operacional usa `pendingOnly`, enquanto o mapa mantém a relação estrutural. Teste de regressão passa.

## Achado adicional corrigido

- **ALTA — Recuperação de backup:** o limite inicial de importação (2 MiB) era menor que backups exportáveis válidos. Reprodução independente: 500 projetos válidos com notas de 3.000 caracteres e objetivo de 1.000 caracteres produziram JSON indentado de 2.192.924 bytes, superior a 2.097.152 bytes. TL confirmou com outra fixture. Correção verificada: teto comum de 32 MiB para importação e backup; guarda antes de salvar; teste de ida/volta de 500 projetos acima do limite antigo restaura todos os dados. Arquivo com teto + 1 byte é recusado sem leitura nem alteração de estado.

Validação de interface permanece com o orquestrador e homologação com o usuário.
