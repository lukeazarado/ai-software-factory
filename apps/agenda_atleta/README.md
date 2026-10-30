# Agenda do Atleta Pro — MVP de autenticação e proteção de dados

Este MVP mantém o HTML 1.6.1 da Agenda do Atleta (agenda, biblioteca, catálogo, relatórios e backups) e acrescenta autenticação Google OpenID Connect no servidor, escopo por conta e criptografia seletiva AES-256-GCM no SQLite.

## Segurança e dados

- **Conta e propriedade**: autenticação real por Google OpenID Connect. O `sub` verificado é convertido em HMAC (com a chave secreta da instância) e usado como identificador interno; o email Google não é persistido. Uma nova conta recebe apenas a sua própria agenda inicial.
- **Autorização**: todas as rotas de listagem, consulta, gravação, atualização e exclusão verificam `owner_id` no banco. IDs de atletas pertencentes a outras contas retornam 404.
- **Criptografia no SQLite**: `athletes.name_enc` e, em `items`, `title_enc`, `school_enc`, `location_enc`, `notes_enc` utilizam AES-256-GCM, nonce aleatório por campo e dados autenticados associados (AAD). Tipo, identificadores técnicos e versão permanecem legíveis; **dia, início e fim** agora são cifrados no campo `schedule_enc`. O novo esquema requer migração aprovada em bancos já existentes. Exportações JSON são **texto claro** e devem ser protegidas separadamente. Não há criptografia ponta a ponta: o servidor acessa o conteúdo em memória.
- **Sessões**: cookies `HttpOnly`, `SameSite=Lax` e `Secure` em HTTPS; token opaco guardado apenas como SHA-256 no banco; expiração em 12h, CSRF por cabeçalho nas operações de alteração e logout; OAuth state, nonce, PKCE S256 e fluxo de uso único.
- **Frontend seguro**: CSS/JavaScript compilados e servidos localmente. `script-src 'self'` e `style-src 'self'` na CSP; sem Tailwind CDN, scripts ou estilos inline no HTML. Arquivos do aplicativo exigem sessão autenticada.
- **Antiabuso**: até 10 inícios de login em 10 minutos por IP de conexão (identificador salvo como HMAC), com HTTP 429 e `Retry-After`; até 500 fluxos OAuth pendentes, com HTTP 503. O IP é o do socket, sem confiar automaticamente no cabeçalho `X-Forwarded-For`. Em redes compartilhadas/NAT, o limite é compartilhado. Para operação pública, adicionar proteção no proxy reverso e monitoramento.
- **Frontend seguro**: CSS/JavaScript compilados e servidos localmente. `script-src 'self'` e `style-src 'self'` na CSP; sem Tailwind CDN, scripts ou estilos inline no HTML. Arquivos do aplicativo exigem sessão autenticada.
- **Antiabuso**: até 10 inícios de login em 10 minutos por IP de conexão (identificador salvo como HMAC), com HTTP 429 e `Retry-After`; até 500 fluxos OAuth pendentes, com HTTP 503. O IP é o do socket, sem confiar automaticamente no cabeçalho `X-Forwarded-For`. Em redes compartilhadas/NAT, o limite é compartilhado. Para operação pública, adicionar proteção no proxy reverso e monitoramento.
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

Para backup consistente do **novo** SQLite (inclusive com WAL ativo), utilize o módulo incluso. Exemplo no PowerShell, com um diretório protegido **fora do repositório**:

```powershell
.\.venv\Scripts\python.exe -m apps.agenda_atleta.backup --output "$env:USERPROFILE\Documents\agenda-segura-backup.sqlite3"
```

O backup nunca sobrescreve um arquivo existente. Guarde `APP_ENCRYPTION_KEY` em local seguro **separado do backup**, pois sem a chave os campos criptografados não podem ser recuperados. O banco contém metadados não criptografados: proteja o arquivo com ACLs e, para cópias externas, criptografia de disco/arquivo. Antes de restaurar: pare o servidor, preserve a cópia atual e restaure para outro arquivo SQLite sem arquivos WAL/SHM antigos. Configure `APP_DB_PATH` para esse arquivo, mantendo a **mesma chave**; confirme que o servidor inicia e que a conta proprietária consegue ler eventos e biblioteca. Um teste automatizado exercita o backup SQLite e a restauração em outro caminho.

Os arquivos JSON exportados **não são criptografados**. Não os compartilhe nem coloque em repositórios.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q tests/test_agenda_atleta.py
```

Os testes automatizados simulam a resposta autenticada do provedor Google sem fazer chamadas reais, e verificam isolamento por proprietário, criptografia, CSRF, expiração, anti-replay OAuth, integridade de dados e falha segura com banco legado ou chave errada. **Não substituem um teste integrado com Google real, navegador e HTTPS.**

## Limitações e riscos antes de produção

- Um login Google autêntico depende do registro/configuração manual das credenciais e do consentimento; teste real do fluxo precisa ocorrer no ambiente de homologação.
- O CSS está compilado localmente e o JS está em `web/app.js`; CSP sem `unsafe-inline` ou origem de CDN. Para modificar utilitários Tailwind, em `apps/agenda_atleta` execute `npm install` (dependência de desenvolvimento livre) e `npm run build:css`. O CSS compilado `web/app.css` é versionado; **Node não é necessário para executar o servidor**.
- A correspondência visual de todos os painéis, gestos, recursos móveis e comportamento do navegador ainda exige homologação manual. A tentativa automatizada de abrir localhost em Chromium foi bloqueada pela política do ambiente de execução, não pelo servidor.
- **Classificação de dados (TL-04):** nome do atleta, nome da atividade, instituição, local e observações são PII e ficam cifrados. Dia e horários são agora cifrados em `schedule_enc` (migração transacional). Tipo e IDs continuam legíveis e podem permitir inferências; ainda é necessária avaliação independente de privacidade, minimização, retenção e proteção de menores. Backups e logs de infraestrutura exigem proteção própria.
- A estrutura é por usuário dono, **sem compartilhamento** de atletas, convites, consentimento parental, auditoria detalhada ou gestão formal LGPD. Esses requisitos devem ser projetados antes de uso público com menores.
- Operação local/homologação apenas até revisão técnica e humana; não criar deploy público, custos, nem merge automático.

## Homologação de login Google real (pendência TL-02)

1. Registrar cliente OAuth **Web**, URI de callback idêntica a `GOOGLE_REDIRECT_URI` e contas de teste autorizadas no console do Google. Não fornecer client secret/chaves pelo chat.
2. Testar autenticação, logout, renovação de sessão por novo login, expiração, cancelamento e erro do provedor; verificar `state`, `nonce` e PKCE.
3. Entrar com **duas contas Google distintas**. Criar atletas e horários em cada uma, tentar consultar/editar IDs da outra conta e confirmar HTTP 404.
4. Em HTTPS de homologação, conferir `Secure`, `HttpOnly`, `SameSite` e CSP pelo DevTools; conferir console sem violação CSP e interface responsiva.
5. Exercitar importação/exportação JSON, catálogos, arrastar e soltar, conflitos, gráficos e backup/restauração usando exclusivamente dados fictícios.
6. Revisão Tech Lead e aprovação humana **separadas** antes de qualquer deploy público.

## Homologação de login Google real (pendência TL-02)

1. Registrar cliente OAuth **Web**, URI de callback idêntica a `GOOGLE_REDIRECT_URI` e contas de teste autorizadas no console do Google. Não fornecer client secret/chaves pelo chat.
2. Testar autenticação, logout, renovação de sessão por novo login, expiração, cancelamento e erro do provedor; verificar `state`, `nonce` e PKCE.
3. Entrar com **duas contas Google distintas**. Criar atletas e horários em cada uma, tentar consultar/editar IDs da outra conta e confirmar HTTP 404.
4. Em HTTPS de homologação, conferir `Secure`, `HttpOnly`, `SameSite` e CSP pelo DevTools; conferir console sem violação CSP e interface responsiva.
5. Exercitar importação/exportação JSON, catálogos, arrastar e soltar, conflitos, gráficos e backup/restauração usando exclusivamente dados fictícios.
6. Revisão Tech Lead e aprovação humana **separadas** antes de qualquer deploy público.

## Solução de problemas: 401 no callback do Google

Se o navegador mostrar `{"detail":"Falha ao verificar identidade Google"}` após o consentimento Google, confirme que o transporte de verificação está instalado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps/agenda_atleta/requirements.txt
.\.venv\Scripts\python.exe -c "from google.auth.transport.requests import Request; print('Transporte Google OK')"
```

Reinicie o processo Uvicorn e **inicie um login novo pela página /login** (o código de autorização e o state são descartáveis e de uso único). O servidor agora registra uma categoria de falha, sem tokens, no formato `Google OAuth callback failed: stage=<etapa> exception=<tipo>`. `token_exchange` indica falha de troca com o Google (verifique Client ID/Secret, redirect URI e rede); `id_token_verification` indica falha ao verificar o token (verifique dependência `requests`, data/hora do Windows e conexão HTTPS de saída). Não altere a chave de criptografia nem remova o SQLite para corrigir erros OAuth.

**Privacidade dos logs:** o log de acesso padrão do Uvicorn inclui a URL completa do callback, com o parâmetro temporário `code`. Para não gravá-lo em logs locais, inicie o servidor com `--no-access-log`. Não cole URLs completas de callback, tokens, Client Secret ou a chave criptográfica em issues, PRs ou chats; para diagnóstico, compartilhe apenas o status HTTP e a categoria de erro.

## Evolução de privacidade e prontidão comercial brasileira

Acesse **Privacidade** no topo da Agenda (ou `/account`) para ver o aviso informativo, registrar declaração do adulto, exportar seus dados e solicitar exclusão da conta (exige CSRF + confirmação literal). **A autodeclaração não verifica tutela ou idade.** O aviso é rascunho e não substitui política de privacidade legalmente aprovada.

### Migração de dia e horários para `schedule_enc`
- Em bancos novos, o SQLite já armazena a agenda em campo cifrado AES-GCM.
- Para bancos seguros anteriores, **pare o servidor e faça backup fora do repositório antes de atualizar**. A versão nova recusa alterar o banco antigo sem `APP_ALLOW_SCHEDULE_MIGRATION=1`.
- Após aprovar o backup/migração, configure temporariamente no PowerShell: `$env:APP_ALLOW_SCHEDULE_MIGRATION = '1'`; inicie a API, confira agendas e depois remova a variável.
- Backups antigos e WAL podem manter dados em texto claro; veja o procedimento de recuperação e descarte em [runbook de operações](../../docs/BR_OPERATIONS_RUNBOOK.md).

### Gates para uso comercial no Brasil
Não anunciar conformidade legal nem vender com dados reais de menores apenas porque o código passou no CI. Consulte [plano de prontidão](../../docs/BR_MARKET_ACCEPTANCE.md) e execute `python -m factory.br_release_gate`; a saída padrão é `NAO_LIBERADO` até comprovar todos os gates jurídicos, comerciais, operacionais e humanos. A aplicação não foi submetida à ANPD para qualquer certificação.
