# Changelog — Plataforma

Cobre Dashboard, Visão geral, Financeiro, Superadmin, empresas,
usuários e integrações administrativas — tudo que **não** pertence ao
mapa. Tags `platform-vX.Y.Z`. Releases em `docs/releases/platform/`.

Para o mapa (editor cartográfico, Rack/Torre, Canvas 2D, fusões, popups,
SNMP, enlaces), ver [CHANGELOG_MAP.md](CHANGELOG_MAP.md).

Histórico anterior a esta separação (quando plataforma e mapa ainda
compartilhavam uma única numeração `vX.Y.Z` global) está em
[CHANGELOG.md](CHANGELOG.md) — as entradas que correspondem ao que hoje
é a trilha de plataforma são `[0.76.0]`, `[0.75.1]`, `[0.75.0]` e
`[0.74.0]` (módulo financeiro, ACL, painel Superadmin, correção de
arquitetura do financeiro — construídos nesta ordem, do zero, nesta
sessão).

## [platform-0.80.0] - 2026-08-02

Cancelar fatura manual (com purga automática em 90 dias) + página de
fatura imprimível/PDF pro cliente. Ver
[docs/releases/platform/platform-v0.80.0.md](docs/releases/platform/platform-v0.80.0.md).

Resumo: Superadmin agora cancela uma cobrança manual lançada por
engano (`Invoice.Status.CANCELED`, já existia no enum, nunca tinha
sido usado); uma task diária nova (`purge_old_canceled_invoices`)
apaga de verdade do banco toda fatura cancelada há mais de 90 dias
(único caso de exclusão física no módulo financeiro, igual ao já feito
pra membro de equipe na v0.78.0). Cliente ganha uma página de fatura
(`/painel/financeiro/faturas/<id>/`) com dados estruturados e histórico
de pagamento, com "Imprimir/Salvar PDF" usando a impressão nativa do
navegador — 3 botões-ícone com tooltip (ver/imprimir/salvar PDF) na
tabela de faturas do Financeiro. Setinhas nativas de `<input type=number>`
removidas em favor do visual flat do tema escuro. Nenhum model novo,
nenhuma migration.

## [platform-0.79.1] - 2026-08-02

Polimento visual do Financeiro por empresa e do Gateway de pagamento.
Ver [docs/releases/platform/platform-v0.79.1.md](docs/releases/platform/platform-v0.79.1.md).

Resumo: os painéis do Financeiro por empresa (Assinatura, Status de
acesso, Lançar cobrança manual, Faturas, Registrar pagamento) estavam
todos espremidos numa única fileira de 4 colunas, forçando barra de
rolagem horizontal em formulário e tabela sem necessidade real —
reagrupados em fileiras de 2. Botões de cabeçalho "Editar empresa"/
"Financeiro"/"Gateway" trocaram de botão sólido grande (`.primary-action`)
por link discreto (`.panel-link`), removendo o exagero visual repetido
em 3 telas. Checkboxes ganharam `accent-color` no tema escuro do site
em vez do azul padrão do navegador. Nenhuma mudança de comportamento,
só CSS/template.

## [platform-0.79.0] - 2026-08-02

Página "Clientes" dedicada no menu do Superadmin — a tabela de
empresas sai da "Visão da plataforma" e ganha página própria, com
link no menu lateral (substitui o item "Nova empresa", que passa a
viver como botão dentro da página). Ver
[docs/releases/platform/platform-v0.79.0.md](docs/releases/platform/platform-v0.79.0.md).

Resumo: item de menu novo "Clientes" → lista de empresas cadastradas +
botão "Nova empresa" → em cada linha, as ações Editar/Financeiro/
Gateway viram botão-ícone com o nome aparecendo em tooltip no hover
(componente CSS novo, reutilizável, sem lib externa). Também corrige
um espaçamento pendente entre painéis empilhados no Financeiro da
plataforma e na tela de Editar empresa (a "barreira" pedida entre
widgets). Nenhum model novo, nenhuma migration.

## [platform-0.78.0] - 2026-08-02

Gestão de empresa e equipe pelo Superadmin — página nova "Editar
empresa" (`painel/plataforma/empresas/<id>/editar/`), ao lado do
Financeiro e do Gateway que já existiam por empresa. Ver
[docs/releases/platform/platform-v0.78.0.md](docs/releases/platform/platform-v0.78.0.md).

Resumo: Superadmin agora edita o cadastro de qualquer empresa (nome,
contato, documento, tipo — inclusive mudar o tipo depois de definido,
coisa que não tinha nenhuma tela funcional até agora) e gerencia a
equipe/acessos dela — adicionar membro, trocar papel (VIEW/EDIT),
ativar/desativar, redefinir senha (novidade: não existia em lugar
nenhum do sistema) e excluir de vez (novidade, com guarda de segurança
pra não apagar acesso do usuário numa empresa diferente por engano).
Nenhum model novo, nenhuma migration.

## [platform-0.77.0] - 2026-08-02

Sistema de financeiro completo do Superadmin — página dedicada nova em
"Financeiro" (menu do Superadmin), consolidando dados de todas as
empresas num só lugar. Ver
[docs/releases/platform/platform-v0.77.0.md](docs/releases/platform/platform-v0.77.0.md).

Resumo: MRR ativo, recebido/pendente/atrasado (valores), taxa de atraso,
gráfico de receita dos últimos 6 meses (CSS puro, sem lib nova), relatório
de faturas em atraso por empresa, lista de empresas com acesso bloqueado,
pagamentos recentes e liberações de confiança recentes — tudo agregado em
`apps/billing/services.py:platform_financial_summary()`, sem nenhum model
ou migration nova. Também corrigida uma barra de rolagem horizontal que
aparecia sempre (mesmo vazia) na tabela de faturas do financeiro do
cliente.

## [platform-0.76.0] - 2026-08-02

Ponto de partida desta trilha separada. Corresponde exatamente ao que
já estava publicado como `v0.76.0` no changelog global (commit
`cf1e118`) — ver a entrada completa em
[CHANGELOG.md#0760---2026-08-02](CHANGELOG.md) e
[docs/releases/v0.76.0.md](docs/releases/v0.76.0.md) pro detalhe
técnico completo. Resumo: correção de arquitetura do financeiro (quem é
cobrado é a empresa cliente — Provedor ISP ou Projetista —, não os
assinantes de internet de cada provedor), painel Superadmin exclusivo
pra cadastro/gestão de empresa e cobrança, liberação de confiança
(+2 dias de acesso, 1x por mês), bloqueio de acesso por assinatura com
fail-safe (empresa sem assinatura cadastrada nunca é bloqueada).

### Infraestrutura de versionamento (nesta mesma trilha)

- `PLATFORM_VERSION`/`MAP_VERSION` separados em `config/settings.py` e
  `docker-compose.yml` — `APP_VERSION` continua existindo só como alias
  de `PLATFORM_VERSION`, pra compatibilidade com código legado.
- Templates passam a ter `platform_version`/`map_version` disponíveis
  (além do `app_version` já existente, agora alias).
- `README.md` — "Versão atual" virou uma tabela com as duas trilhas.
- `docs/releases/platform/` e `docs/releases/map/` criados pra separar
  os releases detalhados de cada trilha daqui pra frente.
