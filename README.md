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
- Para revisão automática em cada PR no futuro, serão necessários um ambiente runner confiável, segredos protegidos, limites de custo e configurações explícitas do GitHub Actions/App.