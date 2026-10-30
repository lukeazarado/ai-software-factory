# Checklist de segurança — Agenda do Atleta

## Escopo da alteração

- **Identidade**: login por Google OIDC (OAuth authorization code, PKCE S256, nonce, state vinculado a cookie, expiração de 10 minutos); usar `sub` verificado por `google-auth`, não email, para identidade.
- **Acesso**: todas as operações por atleta condicionadas ao `owner_id` derivado do usuário autenticado; retornar 404 para outros proprietários.
- **Dados em repouso**: criptografia AES-256-GCM para nome de atleta, título de atividade, escola, local e observações; AAD vincula campo e registro e dificulta troca de ciphertext entre registros. O banco anterior continua intacto.
- **Sessões**: IDs aleatórios armazenados como hashes, cookies HttpOnly/SameSite=Lax/Secure em HTTPS, expirados em 12h, CSRF obrigatório em cada rota mutável, logout revoga sessão.
- **Minimização**: não armazenar email Google, não solicitar serviços ou refresh tokens.

## Ameaças ainda fora do MVP

- Tailwind CDN e scripts inline removidos: JS/CSS agora são servidos apenas da mesma origem, com CSP estrita, sem `unsafe-inline`. O comportamento visual ainda requer homologação no navegador com DevTools e CSP ativa.
- Chave simétrica única: comprometimento do servidor ou da chave permite decriptação de dados; backup consistente incluído, mas proteção externa das cópias e rotação de chave ainda requerem procedimento operacional.
- Sem multi-tenancy organizacional, roles, auditoria de acesso, prevenção adicional de abuso, monitoramento, retenção/expurgo formal, DPA/termos e incident response.
- Backup JSON exportado contém dados em texto claro; tratar como dados pessoais. Na versão v2, dia e horários passam a ser cifrados no campo `schedule_enc`; tipo e IDs técnicos ainda são legíveis e podem permitir inferências. Bancos antigos e backups devem ser migrados/descartados de forma aprovada.
- Login de qualquer conta Google configurada/autorizada cria **seu próprio** espaço isolado. Se o sistema deve ser restrito a convidados, implementar allowlist/convites em etapa posterior.

## Antes de habilitar deploy público

1. Revisão independente do PR pelo Tech Lead e testes reais de autorização (incluindo IDOR e CSRF), dependências e CSP.
2. Configurar OAuth Web Client de produção, HTTPS e domínio, secrets externos ao repositório, backups encriptados e restauração testada.
3. Validar políticas de privacidade, tratamento de dados de menores e medidas LGPD.
4. Criar testes E2E em desktop/mobile, logging seguro, limites de requests, políticas de sessão e conta.
5. Obter aprovação humana específica para custos, credenciais, migração e deploy.

## Revisão pós-ajustes do TL

- **TL-01 (frontend)**: removidos CDN, scripts e estilos inline; CSP restrita e arquivos locais, com testes estáticos e de API. Compatibilidade visual depende de teste E2E manual.
- **TL-02 (Google real)**: pendente com cliente OAuth e HTTPS configurados. Mock de identidade não é evidência de integração real.
- **TL-03 (rate limit)**: 10 tentativas/10min por IP de socket e 500 fluxos globais pendentes. Configure limitação de abuso também no proxy confiável; não use `X-Forwarded-For` sem confiança explícita.
- **TL-04 (classificação)**: a agenda v2 cifra dia e horários no banco ativo, mediante migração aprovada pelo operador; categoria e IDs técnicos permanecem legíveis. Exige decisão e revisão jurídica antes de produção.
- **TL-05 (backup)**: procedimento SQLite consistente (API `.backup`) implementado e verificado por teste de restauração com a mesma chave. JSON continua em texto claro e demanda armazenamento protegido.