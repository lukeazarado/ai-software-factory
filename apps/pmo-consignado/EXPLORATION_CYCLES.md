# PMO — Ciclos exploratórios, 04/11/2026

## Condições
Branch exclusiva `explore/chat-pmo-ux-20261104`; nenhuma alteração direta na `main`. Até 10 ciclos autorizados, não obrigatórios. Os pareceres abaixo são análise dos papéis conduzida no ChatGPT, não execução independente dos agentes Python.

## Ciclo 1 — PO, arquitetura, UX, Dev, QA e TL
- PO: transformar PMO em pauta executiva com riscos, impedimentos e decisões acionáveis.
- Arquiteto: preservar aplicação estática e schema v1; aceitar `issues` e `decisions` opcionais em backups antigos e normalizar para arrays vazios.
- UX: criar seção “Riscos e decisões”, com prazos, responsáveis, recomendações e ações; destacar impedimentos com sinalização própria.
- Dev: persistência local validada, formulários de edição e exclusão, relatório executivo com riscos e decisões do recorte.
- QA: adicionados testes para compatibilidade de backup e rejeição de registros inválidos; **não executados nesta sessão**.
- TL: inspeção estática de risco de migração e validação; não há evidência de execução funcional. Veredito: `NAO_VERIFICADO`.

## Ciclo 2 — PO, arquitetura, UX, Dev, QA e TL
- PO: capacidade sem percentual artificial; simulação sem alterar planejamento.
- Arquiteto: derivar conflitos de períodos de projetos e marcos existentes; reutilizar `impacts` para alcance transitivo.
- UX: duas telas separadas, “Capacidade das squads” e “Simular atrasos”, com explicações de limite do cálculo.
- Dev: indicadores de simultaneidade, marcos em 30 dias, simulação de alcance com data hipotética não persistida.
- QA: pendentes testes de navegador, filtros, dados e acessibilidade.
- TL: cuidado com a distinção entre simultaneidade e ocupação real; não inferir datas ou probabilidade. Veredito: `NAO_VERIFICADO`.

## Ciclo 3 — UX visual e revisão
- PO: tema vermelho para exploração, inspirado em identidade de banco brasileiro, sem alegar vínculo comercial.
- UX: paleta vinho, vermelho carmim, fundos claros, estados de foco e alertas, mantendo a marca própria Órbita.
- Dev: CSS isolado na branch, sem copiar logos ou artes proprietárias.
- QA: pendente aferir contraste e comportamento em 320/375/768 px.
- TL: revisão de diff via comparação de commits; arquivos alterados restritos ao PMO. Sem evidências de CI/E2E ou validação visual. Veredito: `NAO_VERIFICADO`.

## Riscos e bloqueios para homologação
1. **[ALTA]** A suíte e a UI não foram executadas em navegador neste ciclo. Executar testes Node e E2E manuais.
2. **[MÉDIA]** Marcos concluídos sem `actual` podem existir em backups legados; a regra atual permite esse estado. Definir migração e teste antes de endurecer a validação.
3. **[MÉDIA]** A simulação mostra alcance, não cálculo de novos prazos. Não interpretar como previsão quantitativa.
4. **[MÉDIA]** A contagem de simultaneidade não é medição de carga nem disponibilidade da squad.
5. **[BAIXA]** Confirmar contraste e identidade visual no navegador antes de homologar.

## Próxima aprovação
Homologar visualmente e funcionalmente na branch; corrigir problemas identificados; executar suíte; obter revisão TL de diff com evidências; solicitar aprovação humana antes de qualquer merge ou deploy.
