# Agenda do Atleta — Plano de prontidão comercial no Brasil (5 ciclos)

**Status: NÃO LIBERADO PARA PRODUÇÃO OU COMERCIALIZAÇÃO.** Este documento é um registro de engenharia e produto, não é parecer jurídico, certificado LGPD, homologação ANPD nem autorização para operar com dados de menores.

## Premissas da oferta
- MVP: agenda privada de atletas administrada por **adulto responsável** via Google; sem login de menores, redes sociais, perfilamento publicitário, pagamentos ou compartilhamento público.
- Proprietário da conta autentica-se e organiza os atletas; **login Google não comprova idade nem vínculo de tutela**. Eventual declaração é informativa, não prova jurídica de consentimento.
- O operador comercial (razão social, CNPJ/CPF do fornecedor, endereço, canal de contato, política de privacidade, termos e base legal) deverá ser definido por pessoa responsável e assessoria jurídica antes da venda. Não inventar dados do fornecedor.
- A LGPD e o melhor interesse de crianças/adolescentes devem ser avaliados por finalidade e base legal, inclusive dados sobre locais e horários, que podem revelar rotinas. O Enunciado ANPD 1/2023 admite bases legais dos arts. 7º e 11 condicionadas ao melhor interesse; consentimento não deve ser declarado a priori como única base.
- A Lei 15.211/2025 (ECA Digital), vigente desde 17/03/2026, exige análise de aplicabilidade inclusive em serviços de acesso provável por menores. O escopo restrito a adultos **não dispensa** análise jurídica documentada.

## Cinco ciclos com critérios de aceite
1. **PO / Jurídico / TL — mapa de dados e critérios de liberação.** Registro das categorias, finalidade, titulares, riscos e requisitos humanos. Aceite: checklist bloqueia declarações prematuras de conformidade.
2. **Dev / QA — direitos dos titulares e controlador.** Exportar os próprios registros mediante sessão e apagar a própria conta somente após confirmação e proteção CSRF. Aceite: outra conta jamais tem acesso; revogação de sessões após exclusão; sem vazamento entre proprietários.
3. **Arquiteto / Dev — aviso de privacidade e governança infantil.** API versionada de aviso e declaração do adulto, com escopo e registro de data/versão. Aceite: não presumir tutela/consentimento apenas pelo Google; declaração não substitui documentação jurídica.
4. **Dev / QA / TL — confidencialidade da rotina.** Tratar dia e horários como informação pessoal, com criptografia em repouso ou mitigação operacional equivalente. Migração testada de versões anteriores com proteção a perda de dados. Aceite: banco de teste bruto não contém rotinas em texto claro após migração; sem alterar banco local do usuário.
5. **QA / TL / Operações — validação e gate de entrega.** Testes negativos e positivos, revisão de diff, contingência, documentação de incidentes, termos e operação. Aceite: CI verde e lista explícita de itens impeditivos da venda/produção.

## Matriz inicial de dados

| Categoria | Finalidade | Proteção | Risco |
| --- | --- | --- | --- |
| Google `sub` do adulto | Identificar proprietário | HMAC irreversível com chave da instância | Vínculo de identidade persistente |
| Nome do atleta | Identificar agenda | AES-256-GCM | Crianças/adolescentes |
| Atividades, escolas, locais, notas | Planejar rotina | AES-256-GCM | Informação pessoal e inferências |
| Dia e horários | Construir calendário | AES-256-GCM em `schedule_enc`, com migração opt-in | Revela presença em local se houver vazamento de backups antigos |\n| Tipo e IDs técnicos | Operação/calendário | Legível; autorização por proprietário | Inferência de rotinas e correlação |
| Sessão, CSRF e login | Acesso seguro | Cookies HttpOnly / hashes / CSRF | Roubo de sessão |
| Exportação JSON | Portabilidade | Entregue ao dono autenticado; **não cifrado** | Requer guarda cuidadosa |

## Gates humanos obrigatórios antes de declarar pronto para venda
- [ ] Identificar controladora/operadora, fornecedor, contato e determinar base legal e RIPD quando aplicável, com avaliação especializada.
- [ ] Aferir se o ECA Digital se aplica ao público efetivo e realizar medidas exigíveis de prevenção, supervisão e eventual idade, com parecer jurídico.
- [ ] Aprovar política de privacidade pública em português, termos comerciais, contrato de tratamento, canal de direitos, retenção, exclusão e gestão dos titulares.
- [ ] Se houver cobrança: informações de fornecedor, oferta, suporte, cancelamento e direito de arrependimento conforme CDC e Decreto 7.962/2013; definir faturamento/tributação e emissão fiscal.
- [ ] Publicação HTTPS, segredos em cofre, ambientes segregados, monitoração, backup com restauração e incidente testados, controles de rate limiting na borda.
- [ ] Testes reais E2E desktop e celular, autorização cruzada e resposta a incidentes; avaliação independente da proteção de dados de crianças.
- [ ] Definir processo de incidentes e registro: Resolução ANPD 15/2024 prevê comunicação em regra de 3 dias úteis nos casos aplicáveis; avaliar regime de pequeno porte quando couber.
- [ ] Aprovação jurídica + responsável comercial + autorização humana de deploy público.

## Fontes oficiais consultadas (29/10/2026)
- LGPD / crianças e adolescentes: https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/tratamento_de_dados_de_criancas_e_adolescentes.pdf
- Enunciado ANPD nº 1/2023: https://bibliotecadigital.mj.gov.br/bitstream/1/10215/2/Enunciado_ANPD_2023_1.html
- ECA Digital: https://www.gov.br/anpd/pt-br/assuntos/eca-digital/
- ANPD direitos dos titulares: https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares
- Comunicação de incidentes: https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis
- Comércio eletrônico: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/decreto/d7962.htm
