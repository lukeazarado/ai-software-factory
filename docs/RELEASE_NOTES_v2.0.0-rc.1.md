# Agenda do Atleta Pro — v2.0.0-rc.1

**Categoria:** release candidate estável para homologação funcional/controlada.
**Situação comercial:** `NAO_LIBERADO` (não publicar, vender ou cadastrar dados reais de menores sem os gates).
**Base:** PR #8; cinco ciclos de privacidade e operações + consolidação de administração genérica.

## Entregas verificáveis
- Agenda mantém autenticação Google, separação de proprietários e proteção dos dados de atletas.
- Tela **Minha conta e privacidade** em `/account`: fornecedor e documentos parametrizados, declaração versionada, exportação e exclusão de própria conta.
- Tela **Administração** em `/admin` restrita ao administrador configurado pelo servidor: formulários para produto/fornecedor, termos, privacidade, operação e 11 obrigações brasileiras.
- Um único banco SQLite (`APP_DB_PATH`, padrão `data/agenda_atleta_secure.sqlite3`) armazena atletas, sessões, `app_settings`, `app_settings_audit` e evidências. Não há segundo banco de parâmetros.
- Modelo de registro: chave tipada, valor JSON, revisão, autor e instante. Sem novas chaves editáveis arbitrárias nem segredos administrativos.
- Troca de documentos `legal.privacy_notice` ou `legal.terms_of_service` aumenta a versão de aviso e invalida o registro anterior de leitura.
- Comando `python -m factory.br_release_gate --db data/agenda_atleta_secure.sqlite3` utiliza a mesma base para ler as obrigações, mas nunca certifica conformidade.
- A migração anterior de horário para `schedule_enc` **requer backup e consentimento explícito do operador**.

## Exemplos de aceitação (comportamento)
| Evento | Resposta esperada |
| --- | --- |
| Usuário Google não administrativo acessa `/admin` | HTTP 403 |
| Admin autorizado lê `/api/admin/settings` | 11 obrigações + parâmetros, sem dados privados dos atletas |
| Admin tenta alterar OAuth secret na API de parâmetros | HTTP 404: chave não permitida |
| Admin escreve com revisão antiga | HTTP 409: recarregar |
| Admin altera aviso de privacidade | Revisão aumenta, aceite anterior desatualiza |
| Responsável exporta próprios atletas | JSON somente da própria conta (sem criptografia na exportação) |
| Responsável exclui conta sem login recente | HTTP 403 |
| Operador sem evidência jurídica executa gate | `NAO_LIBERADO` |

## Evidências de QA
- `tests/test_admin_settings.py` cobre: banco único, permissão do administrador, isolamento, validação de tipos, CSRF, revisão concorrente, auditoria, versão de aviso, persistência e obrigações.
- A pipeline GitHub Actions instala dependências, compila Python, verifica `node --check` de `app.js`, `account.js`, `admin.js` e executa todos os testes Python.
- Previews desktop/mobile renderizados com HTML/CSS/JS de `web/admin.*` e exemplos fictícios. **Não** são captura de uma sessão real do Google; não homologam OAuth, transação de banco nem E2E de navegação.
- A homologação real em browser de `/admin` e `/account`, restauração de banco pré-migração, testes de teclado/leitor de tela, HTTPS e testes com duas contas Google **continuam pendentes**.

## Controles de liberação
Os trabalhos técnicos desta versão não substituem as decisões legais sobre LGPD, ECA Digital e CDC. `docs/BR_MARKET_ACCEPTANCE.md` e `docs/BR_OPERATIONS_RUNBOOK.md` continuam sendo a lista de bloqueadores antes do lançamento. Nenhum merge, deploy público, custo ou credencial foi autorizado por este documento.

**Produto:** versão candidata completa para avaliação do cliente em homologação. **Comercialização:** não aprovada.
