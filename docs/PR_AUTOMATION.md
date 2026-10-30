# CI e Tech Lead automáticos para Pull Requests

## O que é executado automaticamente

1. Ao abrir, atualizar ou reabrir PR para `main`, o workflow **Testar Agenda do Atleta (CI e manual)** também executa **automaticamente**, com `pull_request` e token somente leitura. Instala dependências, verifica sintaxe e executa `pytest` (suíte do repositório). **Não** recebe segredos e não faz deploy.
2. Quando o workflow termina, **Tech Lead - revisar PR apos QA** recebe um evento `workflow_run`. O código executado é o da **branch padrão confiável**, nunca o código do PR nem artefatos/cache produzidos por ele.
3. O fluxo identifica o PR correspondente, valida repositório, estado e SHA atual para evitar revisão de commit obsoleto ou PR externo, e publica um comentário consultivo no PR. Quando o CI falha, registra `AJUSTES_OBRIGATORIOS` sem gastar tokens. Quando o CI passa mas a IA está desligada, registra `NAO_VERIFICADO`, **não** uma aprovação fictícia.
4. Se o responsável optar explicitamente por habilitar a IA, o `factory.tech_lead` já existente lê o **diff real**, em modo somente leitura, aplica o checklist de `docs/TECH_LEAD.md` e publica o parecer `APROVADO`, `AJUSTES_OBRIGATORIOS` ou `NAO_VERIFICADO`. Ele não aprova formalmente PRs nem executa merge.

## Ativação opt-in do agente de IA (pode gerar custos)

**A automação de testes e do relatório de estado não exige API paga.** A revisão semântica por IA **fica desligada por padrão** até que o responsável aceite os custos e configure, diretamente no GitHub (nunca no chat):

- **Settings → Secrets and variables → Actions → Secrets:** adicionar secret `OPENAI_API_KEY` com escopo do repositório, e aplicar limites de uso/budget no provedor.
- **Settings → Secrets and variables → Actions → Variables:** adicionar `TECH_LEAD_AI_ENABLED` = `true`.
- Opcional: variável `TECH_LEAD_MODEL`, por padrão `gpt-4.1-mini`. O workflow instala o Agents SDK somente quando habilitado.

Após habilitar, cada atualização de PR elegível pode gerar chamadas cobradas à API OpenAI. Pode desligar a qualquer momento alterando a variável para `false`. **Não há nenhuma chave ou valor de segredo no repositório.** Um relatório aprovado é **somente recomendação técnica**; o merge e o deploy permanecem exclusivamente humanos.

## Proteções e limitações

- O segundo workflow usa `workflow_run` privilegiado apenas para ler o GitHub e comentar; **não** faz checkout do código do PR, não executa scripts/artifacts/cache do PR e ignora forks. Valida o SHA e restringe a branch base a `main`.
- Não fornece segredos ao workflow do PR. Permissões mínimas: CI `contents:read`, reviewer `contents:read` + `pull-requests:write` para comentários. Configuração da organização pode proibir comentários do `GITHUB_TOKEN`: nesse caso revisar permissões do GitHub Actions.
- Não existe *merge automático*, *approve review* automático, nem bloqueio obrigatório de branch. Se desejar impedir merge quando CI falhar, configure os **required status checks** e proteções de `main` nas configurações do GitHub, sujeito ao seu plano/permissões.
- Um PR sem patch textual completo, muito grande ou binário é `NAO_VERIFICADO` pela revisão via IA. Textos e diffs são dados não confiáveis (prompt injection); o modelo não executa código.
- Como `workflow_run` é privilegiado, alterações nessa automação devem passar por revisão humana; nunca desabilitar as verificações de origem/commit ou executar arquivos externos ao código confiável.
- O CI automático é uma pré-condição de QA, mas não substitui testes com Google real, navegação, autorização entre usuários e homologação de dados sensíveis.