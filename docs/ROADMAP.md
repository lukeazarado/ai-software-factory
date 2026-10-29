# Roadmap

## MVP 1.0 — incluído neste pacote
- Instruções de orquestração para ChatGPT (4 papéis).
- Executor Python com 4 agentes independentes em sequência, via OpenAI Agents SDK.
- Ferramentas de escrita/leitura limitadas ao workspace do projeto.
- Relatório de requisitos, arquitetura, implementação e QA.
- Template web funcional e testes locais.
- GitHub Actions para testes e deploy manual do template no Pages.

## Próxima etapa — GitHub conectado ao fluxo
- Criar repositório privado `ai-software-factory` e disponibilizar ao conector GitHub.
- Importar o pacote e criar branch de feature e PR para cada alteração.
- Revisão e merge por aprovação humana.

## Depois do MVP
- Integração runner → GitHub por credenciais de instalação com escopo mínimo, em ambiente de execução confiável.
- Jobs assíncronos, logs, limites de custo, políticas de aprovação e sandbox.
- Suporte a backend Java/Spring Boot, banco PostgreSQL e deploy de apps dinâmicos.
- Testes E2E no navegador e análise automatizada de segurança.

## Limites
- ChatGPT não executa automaticamente o script Python a cada mensagem.
- O runner exige OPENAI_API_KEY e ambiente Python externo.
- O deploy no Pages exige repositório GitHub, Pages habilitado e disparo manual.
- Sites estáticos não têm autenticação segura ou banco de dados no servidor.
