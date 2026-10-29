# Agenda do Atleta Pro — MVP com banco de dados

Sistema baseado no HTML **Agenda do Atleta Pro v1.6.1** fornecido pelo solicitante. O HTML/CSS e os componentes de agenda, biblioteca, escolas, gráficos, conflitos de horário, importação/exportação, catálogo Gol de Placa e navegação foram preservados. A única adição visual é um seletor compacto de atleta com ações de cadastrar, renomear e excluir. Os dados de atividades deixam de usar `localStorage`: o servidor grava em SQLite; o navegador só armazena preferências de painéis/menu.

## Executar localmente (Python 3.11+)

```bash
python -m pip install -r apps/agenda_atleta/requirements.txt
# Configure a senha no ambiente de execução, sem incluí-la no código ou no chat.
# PowerShell: $env:APP_PASSWORD = <senha definida no seu ambiente>
# Linux/macOS: export APP_PASSWORD=<senha definida no seu ambiente>
python -m uvicorn apps.agenda_atleta.app:app_factory --factory --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/` e autentique-se com usuário `admin` e a senha definida em `APP_PASSWORD` (mínimo 12 caracteres). O SQLite é criado automaticamente em `data/agenda_atleta.sqlite3`. Para alterar o local, defina `APP_DB_PATH` para um caminho persistente fora do código. **Não coloque o banco em pasta pública nem faça commit dele.**

## Escopo MVP

- Vários atletas, cada um com agenda e biblioteca independentes, cadastro/edição/exclusão.
- Agenda semanal, drag-and-drop, modalidades, escolas, horários, indicadores, conflitos, cartaz e catálogo original.
- Importação JSON validada (até 5 MB pelo navegador e 20.000 itens) e exportação por atleta, compatível com o backup do HTML v1.6.1.
- API HTTP + SQLite transacional, validação de campos, gravação serializada, controle de revisão para detectar edições concorrentes.
- Autenticação HTTP Basic única por instalação, com senha via ambiente. Não há login individual, perfis, histórico de auditoria ou autorização por atleta.

A importação de backups antigos é **manual**: abra o HTML anterior, exporte o JSON; depois, no novo sistema, selecione o atleta desejado e use Importar JSON. A migração não apaga dados antigos do navegador.

## Testes

```bash
python -m pip install pytest httpx
python -m pytest -q tests/test_agenda_atleta.py
```

Testes cobrem autenticação, separação entre atletas, gravação e leitura, reinício da API com mesmo banco, atualização de revisão, conflitos de edição, validações, exclusão e estrutura básica do HTML. Testes E2E em navegador precisam de ambiente que permita acesso HTTP local e devem ser executados antes da homologação.

## Segurança, deploy e limites

- **Não publique na internet sem HTTPS** e autenticação mais robusta/por usuário. HTTP Basic carrega credenciais em cada requisição; só deve ser utilizado sob HTTPS em ambientes restritos de homologação.
- A senha única dá acesso a **todos os atletas**. Para dados pessoais, especialmente de menores, implante identificação e autorização individuais, logs e política de privacidade antes de produção.
- O arquivo original usa Tailwind pelo CDN; mantido para conservar a aparência. Uma evolução deve empacotar CSS local e aplicar Content-Security-Policy.
- Mantenha a instância como processo único para este MVP e faça backup do SQLite antes de atualizações ou migrações.
- Não foi feito deploy. Testes de responsividade, interações completas em navegador e homologação visual ainda são necessários.