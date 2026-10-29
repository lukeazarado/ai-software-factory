# Agenda do Atleta Pro — MVP de autenticação e proteção de dados

Este MVP mantém o HTML 1.6.1 da Agenda do Atleta (agenda, biblioteca, catálogo, relatórios e backups) e acrescenta autenticação Google OpenID Connect no servidor, escopo por conta e criptografia seletiva AES-256-GCM no SQLite.

## Segurança e dados

- **Conta e propriedade**: autenticação real por Google OpenID Connect. O `sub` verificado é convertido em HMAC (com a chave secreta da instância) e usado como identificador interno; o email Google não é persistido. Uma nova conta recebe apenas a sua própria agenda inicial.
- **Autorização**: todas as rotas de listagem, consulta, gravação, atualização e exclusão verificam `owner_id` no banco. IDs de atletas pertencentes a outras contas retornam 404.
- **Criptografia no SQLite**: `athletes.name_enc` e, em `items`, `title_enc`, `school_enc`, `location_enc`, `notes_enc` utilizam AES-256-GCM, nonce aleatório por campo e dados autenticados associados (AAD). Tipo, dia, horários, identificadores técnicos e versão permanecem em texto claro. Exportações JSON são **texto claro** e devem ser protegidas separadamente. Não há criptografia ponta a ponta: o servidor acessa o conteúdo em memória.
- **Sessões**: cookies `HttpOnly`, `SameSite=Lax` e `Secure` em HTTPS; token opaco guardado apenas como SHA-256 no banco; expiração em 12h, CSRF por cabeçalho nas operações de alteração e logout; OAuth state, nonce, PKCE S256 e fluxo de uso único.
- **Configuração**: nenhuma chave ou segredo no GitHub; `APP_ENCRYPTION_KEY` precisa ser mantida de forma segura e estável. Se perdê-la, os dados não serão recuperáveis. A chave errada impede que o servidor inicie.

## Configuração local — Windows PowerShell, Python 3.11+

Crie um cliente OAuth 2.0 de tipo **Aplicativo da Web** no [Google Cloud Console](https://console.cloud.google.com/apis/credentials), configure a tela de consentimento (usuários de teste enquanto estiver em modo de testes) e registre **exatamente** esta URI de redirecionamento autorizada:

`http://127.0.0.1:8000/auth/google/callback`

O fluxo utiliza apenas os escopos `openid email`, sem solicitar acesso a Gmail/Drive/Calendar. Não é necessário habilitar Google Identity Platform; valores/cobranças de hospedagem e outros serviços são separados.

Na raiz do repositório, crie ambiente virtual e instale:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/agenda_atleta/requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest
```

Gere a chave **uma única vez para cada banco** e guarde-a em um gerenciador seguro de segredos. Não compartilhe nem faça commit da chave:

```powershell
.\.venv\Scripts\python.exe -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Configure variáveis de ambiente **na sua sessão local**, com valores obtidos diretamente do console ou do gerenciador de segredos (não os envie pelo chat):

```powershell
$env:APP_ENCRYPTION_KEY = Read-Host "Cole a chave de criptografia previamente guardada"
$env:GOOGLE_CLIENT_ID = Read-Host "Client ID do Google"
$googleSecret = Read-Host "Client Secret do Google" -AsSecureString
$env:GOOGLE_CLIENT_SECRET = [System.Net.NetworkCredential]::new("", $googleSecret).Password
Remove-Variable googleSecret
$env:GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/auth/google/callback"
.\.venv\Scripts\python.exe -m uvicorn apps.agenda_atleta.app:app_factory --factory --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/`. Para uso público, a URI registrada deverá ser **HTTPS** e o processo deverá operar atrás de infraestrutura segura com HTTPS, backup, controles de acesso e observabilidade. Não exponha a instância local diretamente na internet.

## Banco anterior e migração

**NÃO** execute esta versão apontando para o banco antigo `data/agenda_atleta.sqlite3`. A nova versão usa por padrão `data/agenda_atleta_secure.sqlite3`. Se for apontada para um banco antigo, o aplicativo interrompe a inicialização: **não atribui automaticamente atletas antigos ao primeiro usuário a fazer login**.

Para migrar de forma segura:

1. Mantenha uma cópia de segurança do banco antigo, incluindo arquivos WAL/SHM após encerrar o servidor antigo.
2. Com a versão anterior aberta, exporte um arquivo JSON de cada agenda que deseja migrar.
3. Entre nesta nova versão com a conta Google **que será dona dos atletas**, cadastre os atletas e importe cada JSON no atleta correspondente. Revise nome, horários e quantidade de eventos antes de confirmar.
4. Confirme que os dados foram gravados e sobreviveram a um reinício antes de arquivar o backup anterior.

Os arquivos JSON exportados **não são criptografados**. Não os compartilhe nem coloque em repositórios.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q tests/test_agenda_atleta.py
```

Os testes automatizados simulam a resposta autenticada do provedor Google sem fazer chamadas reais, e verificam isolamento por proprietário, criptografia, CSRF, expiração, anti-replay OAuth, integridade de dados e falha segura com banco legado ou chave errada. **Não substituem um teste integrado com Google real, navegador e HTTPS.**

## Limitações e riscos antes de produção

- Um login Google autêntico depende do registro/configuração manual das credenciais e do consentimento; teste real do fluxo precisa ocorrer no ambiente de homologação.
- A interface original utiliza Tailwind CDN e JavaScript/CSS embutidos. Uma fase de hardening deverá compilar o CSS localmente e remover `unsafe-inline` da CSP. A CSP atual reduz algumas superfícies mas não é estrita.
- O banco SQLite tem conteúdo cifrado apenas nos campos selecionados; metadados como horários permanecem visíveis e backups, logs de infraestrutura e sistemas de arquivos exigem proteção própria.
- A estrutura é por usuário dono, **sem compartilhamento** de atletas, convites, consentimento parental, auditoria detalhada ou gestão formal LGPD. Esses requisitos devem ser projetados antes de uso público com menores.
- Operação local/homologação apenas até revisão técnica e humana; não criar deploy público, custos, nem merge automático.