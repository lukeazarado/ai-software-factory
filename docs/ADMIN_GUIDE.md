# Guia administrativo — Agenda do Atleta Pro v2.0.0-rc.1

## Versão e evidência
**Versão:** `v2.0.0-rc.1` — candidata a homologação, sem venda ou deploy público autorizado.
**Banco único de configurações:** `data/agenda_atleta_secure.sqlite3` (padrão), o mesmo arquivo de atletas, sessões e agenda.
**Tabelas:** `app_settings` (chave/valor JSON, versão, autor, data) e `app_settings_audit` (chave, revisão, ator, data), sem duplicar a base. Não persistir segredos ou dados particulares de atletas em parâmetros administrativos.

## Como habilitar o primeiro administrador (sem dar privilégio ao primeiro visitante)
1. Inicie a versão com a **mesma** `APP_ENCRYPTION_KEY` do banco que já usa. Antes de atualizar, faça backup, pois horários de um banco antigo podem exigir migração supervisionada.
2. Entre normalmente com sua conta Google e abra **Privacidade** na Agenda; copie o **identificador da sua conta** exibido na seção de identidade. É um ID pseudonimizado, não o seu email nem a sua senha.
3. Pare o servidor. No **mesmo PowerShell** em que configurou as credenciais Google, execute `$env:APP_ADMIN_OWNER_IDS = "<IDENTIFICADOR_COPIADO>"`. Para múltiplos administradores, separe IDs por vírgula. Nunca coloque essa lista no GitHub.
4. Reinicie o servidor; recarregue a Agenda. O link **Administração** aparecerá para contas autorizadas, levando a `http://127.0.0.1:8000/admin`.
5. Se outro usuário tentar abrir a rota ou as APIs de administração diretamente, receberá `403 Forbidden`, mesmo que esteja autenticado. Essa proteção fica no backend.

**Nota:** o `APP_ADMIN_OWNER_IDS` é uma autorização do ambiente confiável, **não** um parâmetro editável pelo próprio painel. Isso impede que usuários se tornem administradores por manipulação de formulários. Google OAuth Client Secret, chaves AES e tokens também continuam exclusivamente em variáveis/serviço de segredos.

## Parâmetros genéricos
O motor de configuração é **tipado por chave** e verifica limites e valores permitidos:
- `brand.*`: identidade do produto e suporte.
- `supplier.*`: identificação comercial e endereço do fornecedor (dados verdadeiros devem ser fornecidos pelo operador).
- `legal.*`: rascunhos de aviso de privacidade, termos e cancelamento.
- `privacy.*`: público-alvo permitido e **meta planejada** de dias de retenção. A meta não executa descarte automático.
- `operations.*`: canal de incidentes e procedimento de backup.
- `obligation.<codigo>`: 11 requisitos de adequação com `pending`, `in_review`, `evidence_recorded`, responsável, referência da evidência e data. **Evidência registrada não constitui certificação ou aprovação jurídica.**

Cada alteração exige **cookie de sessão válido, permissão administrativa, CSRF, valor compatível com o esquema e revisão atual**. O motor rejeita gravações concorrentes com HTTP 409. Um registro imutável de revisão e ator é acrescentado a `app_settings_audit` (sem copiar valores antigos ou segredos).

## Regras observáveis (exemplos)
1. **Fornecedor:** Admin configura `supplier.legal_name` no painel → dados são gravados no mesmo SQLite → a página Privacidade do usuário lê o nome do fornecedor pela API. Não existe um segundo banco.
2. **Aviso:** Admin muda `legal.privacy_notice` → número de revisão aumenta → o `notice_version` da API muda → aceite anterior do usuário aparece como desatualizado e deve ser renovado.
3. **Isolamento:** usuário comum vê apenas atletas próprios; nunca lê ou edita configurações de toda a operação. O administrador **não ganha** acesso automático a dados dos atletas de outras contas.
4. **Obrigações:** Admin muda `obligation.eca_digital_assessment` para `in_review` → status aparece no painel e no SQLite; sem evidência ou aprovação humana o gate continua `NAO_LIBERADO`.
5. **Auditoria:** duas abas editam a mesma chave com revisão zero → a primeira grava revisão um; a segunda recebe 409 e deve recarregar.
6. **Exclusão:** pedido pelo usuário exige frase exata, CSRF e Google login recente; não é um parâmetro administrativo, pois a segurança de direitos dos titulares é regra obrigatória.

## Checagem comercial a partir do mesmo banco
```powershell
.\.venv\Scripts\python.exe -m factory.br_release_gate --db data/agenda_atleta_secure.sqlite3
```
Retorna `NAO_LIBERADO` enquanto faltarem evidências administrativas. Mesmo com todas as referências registradas, o programa retorna apenas `EVIDENCIAS_DOCUMENTADAS` — **não autoriza o uso comercial automaticamente** e não verifica a autenticidade dos documentos.

## O que exige aprovação humana antes de produção
- Controladora/fornecedor identificado, atendimento e contratos aprovados; base legal, melhor interesse e avaliação jurídica do ECA Digital.
- Backup e restauração comprovados, testes reais HTTPS e OAuth Google, fluxo de titulares, retenção, incidentes e acessibilidade.
- Homologação visual do admin e privacidade no Windows e celular, inclusive alterações concorrentes e roles.
- Aprovação jurídica e autorização específica do responsável para deploy e custos. O merge do PR não constitui esse consentimento.

## Visualizações de homologação
As imagens da entrega foram renderizadas a partir do HTML/CSS/JS do painel com **dados inteiramente fictícios**. Mostram layout e controles, não comprovam execução de OAuth ou gravação real. A evidência funcional automatizada está em `tests/test_admin_settings.py` e no CI do PR.
