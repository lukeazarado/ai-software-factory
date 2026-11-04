# Exploração UX — chat PMO (04/11/2026)

## Objetivo e isolamento
Esta branch é exclusiva para experimentar melhorias na experiência do Órbita PMO Consignado, sem alterar a branch `main`, dados ou regras de negócio. Não equivale a uma execução do agente UX via API; é uma proposta de UX conduzida pelo CTO na conversa.

## Diagnóstico UX (inspeção estática)
- Os filtros existiam sem uma explicação explícita de seu alcance sobre os indicadores.
- A dependência entre cluster e squad era pouco evidente.
- A indicação de armazenamento local merecia maior destaque para reduzir expectativas de sincronização.
- Em larguras estreitas, controles de filtros e barra superior exigem atenção especial.

## Experimento implementado
- Hierarquia textual “Refine sua visão” e explicação de que filtros afetam indicadores e listas.
- Dica contextual para filtro cluster → squad e limpeza de filtros.
- Estado de gravação anunciado com `role=status` e `aria-live=polite`.
- Mensagem de armazenamento reforça a necessidade de backup.
- Regras CSS para ampliar área clicável e acomodar controles em telas estreitas.

## Critérios de aceite para homologação
1. Selecionar cluster e squad deve continuar filtrando o mesmo conjunto de projetos; a dica não pode alterar resultados.
2. Em telas de 320, 375 e 768 px, filtros e botões devem permanecer visíveis e utilizáveis sem rolagem horizontal da página.
3. Leitor de tela deve receber mudanças relevantes de gravação sem anúncios repetitivos excessivos.
4. Layout desktop e ações de backup/importação devem permanecer funcionais.
5. As notas internas continuam ausentes do relatório por padrão.

## Pareceres e limites
- PO: preservação do escopo individual e da semântica existente.
- Arquiteto: mudanças limitadas a HTML/CSS; sem bibliotecas ou backend.
- UX: hipótese de melhoria de compreensão e responsividade; não há pesquisa ou teste de usabilidade executado.
- Dev: arquivos `dist/index.html` e `dist/styles.css` alterados na branch experimental.
- QA: testes de navegador, acessibilidade e regressão ainda pendentes; nenhuma suíte executada nesta conversa.
- TL: `NAO_VERIFICADO` até revisar diff completo e evidências de QA.

## Pendência técnica separada
O núcleo `dist/core.js` aceita importação de marco concluído sem data real, apesar de a interface exigir essa data. Corrigir em uma etapa independente, considerando compatibilidade com backups existentes e testes que simulam conclusão de marcos. Não mudar automaticamente backups de usuários.

## Próximo checkpoint
Comparar visualmente a versão experimental com a `main`, homologar em navegador e escolher quais mudanças manter. Nenhum merge ou deploy autorizado.
