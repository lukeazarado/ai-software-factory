# Agenda do Atleta — runbook operacional Brasil (pré-produção)

Este é um procedimento de **homologação e preparação**, não autoriza vendas/deploy, nem substitui orientação jurídica. Aprovação dos gates em [BR_MARKET_ACCEPTANCE.md](BR_MARKET_ACCEPTANCE.md) e `python -m factory.br_release_gate` é necessária, mas não suficiente.

## 1. Identidade, pessoas menores e finalidade
- Usar login Google **somente de adulto**; o sistema não prova idade, filiação, guarda ou consentimento. A autodeclaração em `/account` é evidência de aceite de aviso, não consentimento válido presumido.
- Estabelecer responsável pelo tratamento/fornecedor e canal público de atendimento antes de comercializar. Avaliar e registrar base legal, melhor interesse de menores, ECA Digital e eventual RIPD com assessor especializado.
- Não usar dados reais de atletas menores durante experimentação; não preencher anúncios com perfis dos atletas.

## 2. Migração segura de horários v1 → v2
**Nunca executar em dados reais sem backup e autorização do operador**. Esta alteração remove as colunas plaintext `day/start/end` e as substitui por `schedule_enc` usando AES-GCM com AAD vinculada ao item.

1. Parar o servidor; identificar o arquivo `APP_DB_PATH` (padrão `data/agenda_atleta_secure.sqlite3`).
2. **Sem expor a chave**: executar o backup SQLite com `python -m apps.agenda_atleta.backup --output <CAMINHO-SEGURO-FORA-DO-REPO>/agenda-antes-migracao.sqlite3`. Verificar integridade e capacidade de restauração com a mesma chave.
3. No primeiro início da versão nova, se detectar o formato antigo, o servidor **recusa migração por padrão**, sem alterar o esquema. Após consentimento do operador e backup, no PowerShell executar `$env:APP_ALLOW_SCHEDULE_MIGRATION = '1'` apenas para a inicialização de migração.
4. A migração é transacional e preserva ciphertext dos campos previamente cifrados. Verificar os atletas/itens e salvar/exportar corretamente; depois remover a variável `APP_ALLOW_SCHEDULE_MIGRATION` e reiniciar normalmente.
5. SQLite WAL, backups antigos, páginas livres e snapshots podem conservar vestígios de horários em texto claro. A migração lógica **não comprova sanitização forense**. Planejar recriação controlada do arquivo e descarte conforme retenção aprovada, sem exclusão automática dos backups.

## 3. Privacidade e direitos
- Rota `/account` oferece aviso **RASCUNHO**, versão, autodeclaração, exportação e exclusão. A política definitiva em português e a identificação do fornecedor precisam de aprovação jurídica.
- `GET /api/account/export` gera JSON de **todos os atletas do próprio usuário**, em texto claro; proteger o arquivo baixado e orientar armazenamento.
- `DELETE /api/account` exige CSRF e confirmação literal, apaga registros da conta ativa e revoga sessões; **não** elimina backups, registros legalmente retidos ou cópias exportadas. Suporte deverá avaliar pedidos de titulares, direitos de terceiros e deveres de retenção.
- Não automatizar exclusão de terceiros por ID; não enviar cópias via e-mail sem avaliação e controles.

## 4. HTTPS e acesso
- Produção exige HTTPS, HSTS em domínio adequado, segredos em cofre, cookies Secure, logs sem token/authorization code, proxy com rate limit e proteção de abuso, origin/CSP verificadas no navegador.
- Para evitar `code` OAuth em logs de request, usar `--no-access-log` no Uvicorn ou sanitização equivalente no reverse proxy. Nunca cole URL de callback completa.
- Conectar contabilidade de custos, níveis de serviço e política de suporte à operação. Não publicar o servidor Uvicorn localhost diretamente.

## 5. Backup, incidentes e resposta
- Executar backup consistente via `sqlite3.backup()`, criptografar **a cópia inteira** e manter `APP_ENCRYPTION_KEY` separada; restaurar num ambiente de teste com a mesma chave.
- Definir janela de retenção de backups, procedimento para exclusão em cópias antigas, rotação de chaves, local de armazenamento e proprietário de contingência.
- Registrar incidentes internamente (sem dados brutos sensíveis em logs), conter, classificar risco e acionar controlador/encarregado. A ANPD prevê comunicação, quando aplicável, em regra em 3 dias úteis; ver regime específico aplicável: https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis
- Sem testes E2E desktop/celular, revisão jurídica LGPD/ECA Digital e evidências de infraestrutura, o gate de comercialização deve permanecer **NAO_LIBERADO**.

## 6. Comando do gate (sem dados pessoais)
```bash
python -m factory.br_release_gate
# Exibe os requisitos pendentes e retorna status 2.
python -m factory.br_release_gate --evidence /caminho/seguro/evidencias-sem-dados-pessoais.json
```
O JSON usa chave do requisito com `approved_by`, `reference`, `approved_on` (ISO date). A validação só verifica a existência formal da referência; ela **não atesta autenticidade, completude ou adequação legal**.

## 7. QA e revisão
- Executar suíte completa `python -m pytest -q` no CI e em ambiente de integração; relatório TL do diff e rastreabilidade do SHA.
- Validar duas contas Google reais com autorização cruzada, inclusão de treino, troca de conta, exportação, exclusão, recuperação de backup, migração de dados antigos e acessibilidade.
- O merge no GitHub **não** significa publicação, e a homologação tecnológica não implica aprovação de operação comercial ou certificado LGPD.
