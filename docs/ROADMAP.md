# Roadmap da AI Software Factory

## MVP 1.0 — concluído
- ChatGPT como CTO Orquestrador e quatro especialistas: Product Owner, Arquiteto, Desenvolvedor e QA.
- Runner Python com quatro agentes, workspace isolado por caminhos e relatório de qualidade.
- GitHub com branch, PR e aprovação humana; template web e testes.

## MVP 1.1 — Squad 2.0 (este PR)
- Quinto agente **Tech Lead**, após QA, com revisão independente e parecer técnico fail-closed.
- Checklist de PR: escopo, arquitetura, segurança, testes, manutenção e riscos.
- Runner de cinco agentes gera relatório com achados, veredito e status para revisão humana.
- Comando opcional `python -m factory.tech_lead` lê diffs via GitHub API (somente leitura) e gera relatório por PR/SHA.
- Atualização das instruções do ChatGPT e AGENTS.md; testes de regressão sem chamadas de API.

## Próximas etapas (não incluídas neste PR)
- Revisão TL disparada automaticamente por eventos de PR no GitHub Actions, com custos aprovados, limites e segredos protegidos.
- Checks obrigatórios de CI/branch protection; regras de aprovação humana e segregação de funções.
- Runner isolado, logs, limites de custo, gestão de incidentes e observabilidade.
- Backend Java/Spring Boot, PostgreSQL e deploy de aplicações dinâmicas conforme demanda.
- Testes E2E reais em navegador e revisão de segurança aprofundada.

## Limites
- A conversa ChatGPT **não executa automaticamente** agentes externos ou pipelines a cada mensagem.
- O runner requer OPENAI_API_KEY; revisão de PR por CLI também requer GITHUB_TOKEN.
- Nenhum parecer do Tech Lead, ainda que favorável, equivale à aprovação humana para merge ou deploy.