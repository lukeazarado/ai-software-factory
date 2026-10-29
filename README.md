# AI Software Factory — MVP 1.0

Fábrica de software multiagente com **ChatGPT como interface principal** e **GitHub como fonte de verdade**.

## O que já funciona
- Instruções prontas para colar em um Projeto do ChatGPT: `CHATGPT_INSTRUCTIONS.md`.
- Executor real de 4 agentes com OpenAI Agents SDK: Product Owner → Arquiteto → Desenvolvedor → QA.
- O desenvolvedor pode gravar arquivos HTML/CSS/JS no workspace com restrições de caminho.
- QA lê os arquivos e realiza verificações estáticas básicas.
- Template web de tarefas com armazenamento local, para demonstrar publicação estática.
- Testes unitários e workflows GitHub Actions.

## 1. Configurar ChatGPT
1. Crie um Projeto no ChatGPT chamado **AI Software Factory**.
2. Cole `CHATGPT_INSTRUCTIONS.md` nas instruções do Projeto.
3. Conecte o GitHub e conceda acesso ao repositório de trabalho.
4. Peça: **"Atue como CTO Orquestrador. Planeje um sistema web de [descrição], com critérios de aceite e implementação em PR."**

**Nota:** os papéis na conversa são uma metodologia de trabalho. Para processos independentes, execute o runner abaixo.

## 2. Criar o repositório
Crie um repositório **privado** chamado `ai-software-factory` na sua conta GitHub, importe os arquivos deste pacote, e autorize acesso à integração do ChatGPT. Não coloque `.env` ou chaves no repositório.

## 3. Executar o runner multiagente (opcional, mas real)
Requer Python 3.11+, acesso à API OpenAI e chave com cobrança configurada. **Não envie a chave pelo chat.**

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
# Linux/macOS: export OPENAI_API_KEY="..."
# PowerShell: $env:OPENAI_API_KEY="..."
python -m factory.runner --project meu-portal --prompt "Crie um gerenciador de tarefas responsivo com persistência local"
```

Saída: `workspace/projects/meu-portal/` e `workspace/reports/meu-portal.json`. Cada execução chama quatro agentes; há consumo de tokens e custo de API. Não publica nem faz commit automaticamente.

## 4. Testar
```bash
python -m pip install pytest
python -m pytest -q
```

## 5. Visualizar o template
Abra `template-web/index.html` em um navegador. Para publicar, habilite GitHub Pages em **Settings → Pages → Build and deployment → GitHub Actions** e execute manualmente o workflow **Publicar template web no GitHub Pages (manual)**. O site fica público: não use dados confidenciais.

## Limites de segurança
- Não há execução arbitrária de shell pelos agentes.
- O workspace restringe extensões e impede caminhos fora do projeto, inclusive via links simbólicos.
- A validação estática é básica, não substitui testes funcionais, E2E ou revisão de segurança.
- O runner roda localmente: para operação contínua, será preciso um executor isolado e observável.
- O template usa localStorage, não possui backend, login real ou armazenamento compartilhado.
