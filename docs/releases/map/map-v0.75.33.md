# MAP v0.75.33 — limpeza do editor óptico e restauração de Rack/Torre

## Problema

As versões v0.75.26 a v0.75.32 fizeram CTO, CEO e CDO abrirem
`openContainerWorkspace`, o mesmo motor/shell Canvas 2D usado por Rack e
Torre — reutilizando e alterando o mesmo DOM interno (`#container-dialog`,
`#map-master-container`, painéis `[data-panel="equipment"]`/`[data-panel="canvas"]`,
`.tower-workspace-actions-v0750`). Isso corrompia esse estado compartilhado
entre aberturas: depois de abrir uma CTO uma vez, reabri-la (ou abrir um
Rack/Torre em seguida) podia falhar com

```
Uncaught TypeError: Cannot read properties of null (reading 'value')
at redrawOpticalLinks
```

```
Uncaught (in promise) TypeError:
Cannot set properties of null (setting 'innerHTML')
at renderEquipmentList
at openContainerWorkspace
```

## Causa raiz

- **`redrawOpticalLinks`**: o código lia `document.getElementById("connection-style")`
  como busca **global**, sem escopo, no `document`. Esse `<select>` só
  existia dentro da barra de ferramentas específica da CTO/CEO/CDO,
  recriada a cada renderização — se o DOM mudasse (outra caixa aberta,
  Rack/Torre aberto depois, resposta assíncrona atrasada), a busca
  retornava `null`.
- **`renderEquipmentList`/`openContainerWorkspace`**: `ensureContainerWorkspace()`
  constrói `#map-master-container` **uma única vez** e o reaproveita em
  toda abertura seguinte (por design, para não perder estado do Rack/Torre
  entre aberturas). A integração experimental fazia CTO/CEO/CDO
  compartilhar esse mesmo elemento e inserir/remover nós próprios
  (`.cto-embedded-canvas-v07530`, botões extras na barra de ações,
  widget de portas) através de `updateContainerIdentity()` — a mesma
  função usada por Rack e Torre, agora com muitos ramos condicionais só
  da CTO. Qualquer mutação incompleta ou fora de ordem nesse template
  singleton deixava o Rack/Torre com um DOM inconsistente na abertura
  seguinte.

## Solução: remoção completa, não patch

Por decisão explícita, esta versão **não tenta corrigir** a arquitetura
compartilhada — ela é removida por inteiro:

- `static/js/map-cto-suite.js` apagado do repositório; `templates/map.html`
  não carrega mais nenhum script do módulo óptico experimental.
- `map-editor.js`: dispatch de clique no marcador e menu de contexto
  voltam a não chamar `openContainerWorkspace` para `cto`/`splice_box`.
  Em vez de reabrir o antigo `#unifilar-dialog` (proibido como "solução
  improvisada"), mostram apenas: *"Editor óptico temporariamente
  desativado para reconstrução."*
- `map-v0758-core-ui.js`: `containerIdentity`/`updateContainerIdentity`
  revertidas à versão anterior à integração — só `rack`/`tower`. Removidos
  `ensureCtoEmbeddedCanvas`, `triggerCtoAction`, `updateCtoPortsWidget`,
  o contador de geração `opticalBoxRenderGeneration` e o listener de
  `close` que descartava `window.mapCtoSuite`.
  `static/js/map-v0750-tower-workspace.js`: o botão "Fibras" volta a só
  alternar o destaque do Canvas do Rack/Torre.
- `static/css/map-v0758-core-ui.css`: revertido ao estado anterior à
  integração, preservando a única correção genuína encontrada no meio do
  diff (`.tower-workspace-actions-v0750 [hidden]`/`.tower-popover-v0750
  [hidden] { display: none !important; }` — um bug real de cascata CSS do
  Rack/Torre, não específico da CTO).
- Backend: os 5 endpoints do shell comum (`container_equipment`,
  `container_port_links`, `container_layout_v3`,
  `create_passive_endpoint_v3`, `import_container_device_type_yaml`)
  voltam a aceitar só `RACK`/`TOWER`.
- `renderEquipmentList` (`map-master-suite.js`, nunca editado pelas
  versões da integração) ganhou uma guarda defensiva: se
  `[data-panel="equipment"]` não existir, registra o erro no console e
  retorna, em vez de derrubar o editor inteiro.
- Os 7 testes de contrato "congelados" das versões v0.75.26–v0.75.32
  (que travavam exatamente a arquitetura agora removida) foram apagados
  junto com o código que verificavam.

## `reset_optical_test_data`

Comando novo (`python manage.py reset_optical_test_data`) para relatar e,
com `--confirm`, limpar resíduos da integração quebrada:

- Relata o inventário de CTO/CEO/CDO: quantas caixas, quantos splitters,
  bandejas de emenda, fusões, portas de splitter (e quantas estão
  ocupadas por `access_point` real de cliente) e cabos conectados.
- **Nunca apaga** splitters, bandejas ou fusões reais — os models não têm
  nenhuma marca de "criado durante o teste da integração quebrada"; uma
  CTO de teste e uma CTO real de cliente têm exatamente a mesma forma
  nos dados, então apagar ali arriscaria derrubar atendimento real.
- Remove apenas o que é estruturalmente impossível de ser dado legítimo:
  registros de "equipamento genérico" (modelo do Rack/Torre,
  `ContainerEquipment`) presos numa CTO/CEO/CDO — só existem porque o
  endpoint quebrado deixava isso passar — e a chave de metadata
  `container_layout_v3` (layout do Canvas do Rack/Torre) órfã numa caixa
  óptica.
- `--dry-run` (padrão sem `--confirm`) só mostra o relatório.
  `--confirm` executa a limpeza dentro de `transaction.atomic()`.

## Compatibilidade

Preservados sem alteração: Rack, Torre, OLT, equipamentos, portas de
equipamento, cabos, rotas, postes, mapa, clientes, integração IXCSoft,
autenticação e permissões. Nenhuma migration. CTO/CEO/CDO ficam
temporariamente sem editor óptico interativo, preparando terreno para a
reconstrução isolada (arquivo/arquitetura próprios, sem depender do DOM
do Rack/Torre).
