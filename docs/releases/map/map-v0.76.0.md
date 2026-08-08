# MAP v0.76.0

Corte real de cabo em CTO/CEO/CDO, rotas com CTO exclusiva e CEO/CDO
compartilhável, e ocupação de porta de splitter por PPPoE (ERP) ou DROP
físico.

## Contexto

O usuário forneceu um pacote de handoff completo (`AFService Map
Handoff — route/cut v0.76`: `payload/`, `apply_changes.py`, `verify.py`,
`EXPECTED_BASE_FILES.json` com blobs Git, `TEST_PLAN.md`) preparado
contra o commit `32a27e3`. Segui o procedimento pedido: verifiquei a
integridade (`verify.py`, OK), confirmei que o HEAD atual só diverge do
commit-base do pacote por arquivos que o pacote não toca (meu próprio
PR de platform-v0.84.0, sem overlap), apliquei numa branch nova
(`fix/map-route-cut-v076`) e revisei o diff inteiro linha a linha antes
de rodar qualquer teste ou commitar — a pedido explícito do usuário
("o handoff é uma implementação proposta, não uma ordem para ignorar
bugs").

## O que muda

### Corte de cabo

`POST /api/map/elements/<element>/cables/<cable>/cut/`
(`apps/network_map/api/topology_actions.py`) deixou de bloquear quando
já existem fusões/terminações/splitters usando o cabo. Em vez disso:
projeta a caixa sobre a geometria real do cabo, separa em dois
`LineString`, cria um segundo `FiberCable` com sua própria estrutura de
fibras (clonando tubos/fibras quando o cabo não tem `cable_model`, ou
via `generate_cable_fibers` quando tem), e migra pra esse segundo cabo
todas as referências ópticas (`FiberSplice`, `SpliceTraySplitter`,
`SpliceTraySplitterPort`, `CTOSplitter`, `ContainerPortLink`) e de
topologia (`CableElementPassage`, reservas, postes) que ficam a jusante
do ponto de corte — decidido por proximidade geométrica ou, na própria
caixa do corte, pela semântica `input_fiber` (chegada, fica no 1º
trecho) vs `output_fiber` (distribuição, migra pro 2º). Os dois cabos
são renomeados automaticamente pelos endpoints
(`CABO CTO 1 → CTO 3 12 F` cortado na CTO 2 vira `CABO CTO 1 → CTO 2
12 F` + `CABO CTO 2 → CTO 3 12 F`).

### Rotas

`CTO.route` continua sendo a fonte de verdade pra exclusividade — uma
segunda tentativa de rota devolve HTTP 409 `"Essa CTO já tem rota."`
(`apps/network_map/api/optical_editor_v3.py::assign_asset_route_v3`).
CEO/CDO ganham `NetworkRouteElementMembership` (nova tabela,
`apps/network_map/models.py`), permitindo a mesma caixa em várias
rotas sem transformar o resto do sistema em N:N. `POST
/api/map/routes/` (`apps/network_map/project_api.py`) cria rota nova
com código único gerado automaticamente. Na interface
(`static/js/map-master-suite.js`), o botão "Rotas" aparece mesmo sem
nenhuma rota cadastrada, com "+ Nova rota"; botão direito no cabo
(`static/js/map-v07539-suite.js`) e em CTO/CEO/CDO
(`static/js/map-v0758-core-ui.js`) ganham "Adicionar na rota" — a
"Editar traçado" (edição de geometria), que tinha sido fundida com
isso numa rodada anterior (v0.75.57), volta a ser uma ação separada.

### Splitter — PPPoE vs DROP físico

`PATCH /api/map/master/ctos/<cto>/splitter-ports/`
(`apps/network_map/api/map_master_views.py`) ganha `access_point_id`
(vincula um AccessPoint/PPPoE do ERP — ocupa a porta sem criar nenhuma
`FiberStrand`, é associação lógica/comercial) e `direct_drop_cable_id`
(vincula um cabo DROP desenhado manualmente — ocupa a porta como
ligação física real). Quando o DROP já foi desenhado direto no canvas
(sem passar por essa API), a ocupação é derivada automaticamente via
`SpliceTraySplitterPort.output_fiber` pela posição do splitter/porta,
marcada como `"source": "manual_canvas"` no payload pra diferenciar de
uma vinculação manual (`"source": "port_binding"`).

## Achados na revisão (corrigidos além do pacote original)

1. **DROP duplicado quebrava com HTTP 500**: `direct_drop_cable` é
   `OneToOneField` — vincular um cabo já ocupado por outra porta
   estourava `IntegrityError` sem tratamento. Adicionei checagem
   explícita antes do `save()`, devolvendo 409 com mensagem clara.
2. **A linha fixa do splitter existia em dois lugares que o pacote não
   tocou**. O pacote corrigiu `#unifilar-dialog` em `map-editor.js`,
   mas esse é código morto hoje — a view real usada em produção pra
   abrir fusões de CTO/CEO/CDO é o `IXCOpticalWorkspace` (confirmado
   lendo o handler de clique/menu de contexto). Achei o traço fixo de
   verdade em **dois pontos independentes**, nenhum tocado pelo
   handoff:
   - `drawDistributionDivider()` em `static/js/optical/optical-renderer.js`
     desenhava um traço tracejado sempre, no Canvas 2D, sem relação com
     nenhuma fibra/conexão real — removido, mantendo só os rótulos de
     orientação ("ENTRADA / CHEGADA", "SAÍDA / DISTRIBUIÇÃO");
   - a classe `ixc-optical-stage-has-divider`
     (`static/js/optical/optical-workspace.js`), aplicada
     incondicionalmente no HTML do workspace, gerava OUTRA linha e
     rótulo duplicado via pseudo-elementos CSS
     (`static/css/map-optical-workspace-v07535.css`,
     `static/css/map-v07539-suite.css`) — removida a classe e as
     regras CSS mortas.

   Confirmado visualmente via Playwright (Docker isolado): antes e
   depois de cada correção, com screenshot comparando a mesma CTO —
   linha sumiu nos dois casos, splitter/portas/fibras/conexões reais
   continuam intactos.

## Validação

- `apps/network_map/tests/test_route_cut_v076.py`: 4 testes estáticos
  originais do pacote + **16 testes funcionais novos** (Django
  `TestCase` real, banco de verdade) cobrindo os 6 cenários
  obrigatórios do `TEST_PLAN.md`: corte com fusão ativa nos dois lados
  (na própria caixa e a jusante), nomes/contagem de fibra dos dois
  segmentos, corte repetido é no-op seguro, CTO exclusiva (409), CEO/
  CDO em duas rotas (2 memberships confirmados), criação de rota com
  código único, PPPoE sem fibra sintética, DROP ocupando porta, DROP
  duplicado rejeitado (409).
- `python manage.py check`, `makemigrations --check` (drift restante é
  100% pré-existente, não relacionado — `billing.monthly_amount`,
  `core.erp_provider`, renomeações de índice em `network_map`/
  `snmp_monitoring` já existiam antes desta mudança).
- Suíte completa `apps.network_map` (61 testes) + `apps.core
  apps.billing` (18 testes): só as 2 falhas antigas e não relacionadas
  já conhecidas (ordenação de scripts em `map.html`).
- Suíte de contratos da raiz (`tests/`, 360 testes,
  `python -m unittest discover`): comparado contra baseline real no
  commit-base do handoff (`git worktree` em `32a27e3`) — 49 falhas
  pré-existentes em ambos, **zero novas**. Corrigi de passagem 15
  falhas que essa suíte já tinha por causa do meu próprio PR anterior
  (platform-v0.84.0) nunca ter rodado essa suíte específica antes do
  merge (`PLATFORM_VERSION` desatualizada em vários `tests/test_map_v075XX_contract.py`,
  contagem de migration desatualizada em 1 arquivo, e 1 asserção que
  descrevia o comportamento antigo "Editar rota" fundida — atualizada
  pra refletir a separação desta versão).
- Validação real no navegador (Playwright, Docker isolado no
  servidor): ADMIN cria rota nova end-to-end; diálogo de rota do cabo/
  elemento abre com o título certo; hover em CTO mostra o nome; botão
  direito em CTO mostra "Adicionar na rota"; linha fixa do splitter
  confirmada removida visualmente (antes/depois).

## Ainda pendente / riscos conhecidos

- Corte só opera sobre o primeiro `LineString` de cabos com geometria
  `MultiLineString` de múltiplos componentes independentes (mesmo
  comportamento já existente antes desta mudança).
- Remover CEO/CDO de uma rota específica (mantendo outras) não tem
  ação dedicada na interface hoje — só "adicionar mais uma" ou "limpar
  todas" (`NetworkRouteElementMembership.objects.filter(element=...).delete()`
  remove tudo de uma vez). Não bloqueia nenhum dos cenários pedidos,
  mas é uma limitação de UX pra uma rodada futura se o usuário precisar
  disso.
- Sem migration de dado pra `PLATFORM_VERSION`; nenhuma alteração na
  trilha Plataforma nesta rodada.
