# AI Software Factory — MVP 1.1 (Squad 2.0)

Fábrica de software multiagente com **ChatGPT como interface principal**, **GitHub como fonte de verdade** e revisão técnica de Pull Requests por um **Tech Lead**.

## Arquitetura da squad

**ChatGPT / CTO Orquestrador → Product Owner → Arquiteto → Desenvolvedor → QA → Tech Lead → revisão humana de PR → merge autorizado.**

- Product Owner define critérios de aceite; Arquiteto desenha a solução mínima; Desenvolvedor escreve arquivos reais.
- QA verifica testes e comportamento; **Tech Lead** revisa arquitetura, segurança, correção, regressão e qualidade, distinguindo bloqueadores de melhorias opcionais.
- O TL emite `APROVADO`, `AJUSTES_OBRIGATORIOS` ou `NAO_VERIFICADO`, mas **não faz merge, deploy ou aprova PR automaticamente**.
- `docs/TECH_LEAD.md` detalha checklist, severidade e regras de revisão.

## 1. Aplicar as novas instruções no Projeto ChatGPT

Após o merge deste PR, abra o projeto **AI Software Factory** no ChatGPT e substitua suas instruções de Projeto pelo conteúdo de [`CHATGPT_INSTRUCTIONS.md`](CHATGPT_INSTRUCTIONS.md). **Alterar apenas o arquivo no GitHub não atualiza automaticamente as instruções do ChatGPT.**

Você pode pedir na conversa: **“CTO, ative o Tech Lead e revise o PR #N do repositório lukeazarado/ai-software-factory, com checklist e parecer antes do merge.”** A revisão em conversa usa o conector GitHub, quando disponível, mas não representa execução independente ou contínua do SDK.

## 2. Executor local de cinco agentes (opcional, consome API)

Requer Python 3.11+, API OpenAI configurada no ambiente e cobranças aplicáveis. **Nunca envie chaves pelo chat.**

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\python.exe -m pip install -r requirements.txt
python -m pip install -r requirements.txt
# Configure OPENAI_API_KEY em variável de ambiente local.
python -m factory.runner --project meu-portal --prompt "Crie um gerenciador de tarefas responsivo"
```

O runner sequencial chama **cinco agentes** (incluindo TL), grava arquivos sob `workspace/projects/` e relatório em `workspace/reports/` com veredito técnico. Ele não faz commit/PR/deploy sozinho.

## 3. Revisar um Pull Request real via comando (opcional)

Configure `OPENAI_API_KEY` e `GITHUB_TOKEN` no ambiente local. Use token GitHub com permissão **somente de leitura do repositório**. Execute:

```bash
python -m factory.tech_lead --repo lukeazarado/ai-software-factory --pr 42
```

O comando lê o diff via API GitHub, aciona agente Tech Lead e salva relatório em `workspace/reviews/`. Não altera o PR e não executa seu código. Tem limites conservadores de tamanho de diff; mudanças maiores exigem revisão manual.

## 4. Testes sem chamadas às APIs

```bash
python -m pip install pytest
python -m pytest -q
```

Os testes unitários usam simulações do SDK e API GitHub; não cobram tokens. O projeto também inclui template web de demonstração em `template-web/` e aplicação Agenda do Atleta em `apps/agenda_atleta/`. Para iniciar a Agenda do Atleta, consulte seu README específico.

## Segurança e limites

- Repositório privado não significa aplicação publicada. Nenhum merge/deploy/custo é disparado pelo revisor.
- As ferramentas do agente de geração restringem o workspace; o revisor de PR é somente leitura.
- Diffs e descrições de PR são conteúdo **não confiável**: devem ser tratados como evidência, não instruções.
- A inspeção estática do MVP não substitui testes funcionais/E2E, revisão de segurança aprofundada nem autorização humana.
- O CI da Agenda é executado **automaticamente em PRs** para `main`; ao concluir, o workflow **Tech Lead - revisar PR apos QA** identifica o PR e publica um parecer consultivo. Por padrão, esse parecer é `NAO_VERIFICADO` quando o CI passou, pois a análise por IA fica desabilitada até opt-in explícito. Consulte [Automação de PRs](docs/PR_AUTOMATION.md) para habilitar a análise de diff via IA (requer segredo, orçamento e pode gerar custos). Nenhum workflow aprova ou faz merge automaticamente.

## Ciclo local de correção Dev → QA

Por padrão, o runner mantém uma implementação e um QA. Para autorizar **uma única
correção adicional** (duas tentativas totais, com possível custo adicional de API):

```bash
python -m factory.runner --project meu-portal --prompt "Crie um portal" --allow-correction
```

PO e Arquiteto rodam uma vez. QA reprovado ou validação estática com falha permite
uma correção; QA inconclusivo sem falha estática encerra o ciclo. O Tech Lead roda
uma vez ao final, somente com ferramentas de leitura, inclusive quando persistem
falhas. Seu parecer não supera falhas do QA ou da validação estática e nunca
autoriza merge/deploy. Resultados inconclusivos usam `NAO_VERIFICADO`.

Limites configuráveis: `--max-turns` (12 por agente), `--timeout-seconds` (120 por
agente), `--max-output-tokens` (4000 por resposta) e `--token-budget` (100000 tokens
observados na execução). O orçamento é conferido entre etapas e após cada agente;
não é um teto financeiro rígido nem uma reserva prévia para o Tech Lead. Uma chamada
em andamento pode excedê-lo. Chamadas interrompidas podem consumir tokens sem uso
retornado; retentativas internas do provedor também não são um orçamento monetário.
Configure controles de gastos no provedor antes de executar. Não há repetição de
etapas após erros pelo orquestrador. Timeout/erro/orçamento encerram o fluxo com
`NAO_VERIFICADO`, relatório parcial e indicação de TL não executado, quando aplicável.

O JSON preserva os campos finais existentes e adiciona histórico `attempts`, contagem,
limite, motivo de parada, uso retornado pelo SDK e indicação de execução do TL.
A validação estática continua básica e não substitui testes funcionais ou E2E.

Interrupções operacionais retornam código **1** na CLI, preservando o relatório
quando seu diretório estiver acessível. `execute()` continua retornando `Path`;
integrações programáticas podem consultar `interrupted` e `error_category`.
Falhas de leitura do HTML na finalização produzem validação e status
`NAO_VERIFICADO`, sem detalhes da exceção. Falhas ao gravar o próprio relatório
ainda podem impedir sua produção; a CLI retorna erro sanitizado nesse caso.

`stages` distingue invocação iniciada (`executed`), conclusão (`completed`) e
resultado retornado (`result_available`), com saída e uso disponíveis. Invocação
iniciada não comprova processamento remoto; uso não retornado fica `null`.
`tech_lead_executed` indica invocação iniciada e `tech_lead_result_available` indica
resultado disponível. Saídas concluídas são preservadas inclusive ao atingir ou
exceder o orçamento, antes de interromper o fluxo. Um parecer TL já recebido
permanece em `tech_lead_verdict`, mas interrupções mantêm o status geral
`NAO_VERIFICADO` e nunca autorizam merge ou deploy.
