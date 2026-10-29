# Checklist de segurança — Agenda do Atleta

## Escopo da alteração

- **Identidade**: login por Google OIDC (OAuth authorization code, PKCE S256, nonce, state vinculado a cookie, expiração de 10 minutos); usar `sub` verificado por `google-auth`, não email, para identidade.
- **Acesso**: todas as operações por atleta condicionadas ao `owner_id` derivado do usuário autenticado; retornar 404 para outros proprietários.
- **Dados em repouso**: criptografia AES-256-GCM para nome de atleta, título de atividade, escola, local e observações; AAD vincula campo e registro e dificulta troca de ciphertext entre registros. O banco anterior continua intacto.
- **Sessões**: IDs aleatórios armazenados como hashes, cookies HttpOnly/SameSite=Lax/Secure em HTTPS, expirados em 12h, CSRF obrigatório em cada rota mutável, logout revoga sessão.
- **Minimização**: não armazenar email Google, não solicitar serviços ou refresh tokens.

## Ameaças ainda fora do MVP

- O Tailwind CDN e código inline reduzem proteção CSP. Antes de liberar publicamente, empacotar JS/CSS local e aplicar CSP estrita e SRI quando necessário.
- Chave simétrica única: comprometimento do servidor ou da chave permite decriptação de dados; backup seguro e rotação de chave ainda não implementados.
- Sem multi-tenancy organizacional, roles, auditoria de acesso, prevenção adicional de abuso, monitoramento, retenção/expurgo formal, DPA/termos e incident response.
- Backup JSON exportado contém dados em texto claro; tratar como dados pessoais. Campos não cifrados incluem horários, tipo e IDs técnicos (com eventual inferência de rotinas).
- Login de qualquer conta Google configurada/autorizada cria **seu próprio** espaço isolado. Se o sistema deve ser restrito a convidados, implementar allowlist/convites em etapa posterior.

## Antes de habilitar deploy público

1. Revisão independente do PR pelo Tech Lead e testes reais de autorização (incluindo IDOR e CSRF), dependências e CSP.
2. Configurar OAuth Web Client de produção, HTTPS e domínio, secrets externos ao repositório, backups encriptados e restauração testada.
3. Validar políticas de privacidade, tratamento de dados de menores e medidas LGPD.
4. Criar testes E2E em desktop/mobile, logging seguro, limites de requests, políticas de sessão e conta.
5. Obter aprovação humana específica para custos, credenciais, migração e deploy.