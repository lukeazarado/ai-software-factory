# Tech Lead — padrão de revisão de Pull Requests

## Responsabilidade
Revisar a qualidade técnica e o risco de entrega **após a implementação e o QA**, antes da decisão humana. O Tech Lead pode recomendar ajustes ou aprovar tecnicamente uma proposta, mas **nunca autoriza sozinho merge ou deploy**. Não substitui testes automatizados nem o QA.

## Checklist de review
1. **Escopo e comportamento:** critérios de aceite, bugs, casos-limite, mudanças inesperadas, regressões e compatibilidade.
2. **Arquitetura:** aderência à stack do produto, limites de componentes, dependências, complexidade proporcional ao MVP.
3. **Segurança e dados:** autenticação/autorização, validações, injeção, segredos, exposição de dados, privacidade, migrações e recuperação.
4. **Qualidade:** clareza, coesão, nomes, tratamento de erros, testes proporcionais ao risco, ausência de duplicação relevante.
5. **Operação:** desempenho, logs sem segredos, configuração, falhas, rollback, documentação e monitoramento quando necessário.
6. **Evidências:** distinguir inspeção estática, testes realmente executados e validação em navegador/produção ainda não feita.

## Severidade e veredito
- **BLOQUEANTE:** risco imediato de vazamento, perda de dados, falha grave de lógica ou entrega impossível.
- **ALTA:** regressão provável, segurança relevante, ausência de teste essencial para mudança crítica.
- **MEDIA:** risco moderado de manutenção/correção ou lacuna de validação relevante.
- **BAIXA:** melhoria opcional, pequena simplificação, estilo não crítico.

Vereditos possíveis:
- `APROVADO`: sem bloqueadores encontrados no material efetivamente analisado. Significa **apenas parecer técnico favorável**; exige validação humana para merge.
- `AJUSTES_OBRIGATORIOS`: existe bloqueador a corrigir antes da recomendação de merge.
- `NAO_VERIFICADO`: faltam evidências ou acesso ao diff/arquivos/testes para concluir.

Formato do parecer:

```text
Resumo: ...
Achados:
- [ALTA] caminho/arquivo.ext:linha — evidência, impacto e correção proposta
Checklist: escopo / arquitetura / segurança / testes / operação
Testes: executados, não executados, riscos
Risco residual e rollback: ...
VEREDITO: AJUSTES_OBRIGATORIOS
```

## Uso pela conversa no ChatGPT
Após implementar e abrir um PR, peça **“CTO, ative o Tech Lead e revise o PR #N da AI Software Factory antes de aprovar.”** O orquestrador deve acessar o diff e os arquivos reais pelo GitHub conectado, relatar os achados e a recomendação. Não realizar merge automaticamente.

## Uso independente em ambiente Python (opcional)

```bash
# Python 3.11+; configure OPENAI_API_KEY e GITHUB_TOKEN localmente.
# Nunca envie credenciais no chat nem as grave no repositório.
python -m pip install -r requirements.txt
python -m factory.tech_lead --repo lukeazarado/ai-software-factory --pr 42
```

A saída é um JSON em `workspace/reviews/` com o SHA do PR, parecer e veredito, **sem comentar nem aprovar o PR no GitHub**. O comando consome tokens da API e exige execução intencional; não é acionado automaticamente quando um PR é criado. Os diffs são lidos sem execução de código não confiável. Arquivos binários, diffs ausentes e PRs muito grandes exigem revisão manual. Como o parecer é por diff, o revisor pode necessitar de contexto adicional para validação completa.

## Integração automática com GitHub Actions

Todo PR direcionado à `main` aciona CI de testes com token somente leitura. Após a conclusão, o workflow confiável de Tech Lead faz uma verificação de elegibilidade por SHA/PR, publica um comentário com a conclusão do CI e, se houver opt-in explícito via secret `OPENAI_API_KEY` e variável `TECH_LEAD_AI_ENABLED=true`, chama o agente para revisar o diff sem executar código do PR. Na ausência de autorização de custos, o resultado é `NAO_VERIFICADO` após CI verde e a revisão humana continua necessária. CI vermelho resulta em `AJUSTES_OBRIGATORIOS`.

Detalhes e configuração: [Automação de Pull Requests](PR_AUTOMATION.md). Isso **não** configura merge automático, aprovação formal no GitHub, deploy ou branch protection.

## Limites do MVP
O pipeline `factory.runner` contém cinco agentes por padrão e pode incluir o UX Designer com `--enable-ux`; registra o parecer de Tech Lead no relatório local. O UX participa apenas do desenho, antes da implementação, e o TL permanece independente. Esse runner **não cria PRs**. O GitHub Actions agora integra testes em PRs e relatório TL após CI, sem execução paga até opt-in. Não há branch protection obrigatória configurada, autorização de merge automático nem deploy automático.
