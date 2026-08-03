# MAP v0.75.9 — elimina renderização duplicada e restaura o Canvas

**Data:** 2026-08-03
**Base:** `67077444659639bec037a56632c95a611fe566a8`
**Plataforma preservada:** `0.82.0`
**Mapa:** `0.75.9`

## Contexto

Investigação read-only da v0.75.8 (sem alterar nada) levantou hipóteses
sobre 7 sintomas relatados na homologação do Debian. O Adrian então
forneceu os dados reais do banco pros pontos de teste — **nenhum tinha
registro duplicado**. Isso descartou a hipótese de dado sujo e confirmou
que a causa raiz era 100% frontend: dois renderers reagindo à mesma
abertura de Rack/Torre, um `MutationObserver` disparando carregamento
por baixo dos panos, e um corte de propagação de evento que só rodava
depois de checagens que podiam falhar.

## Causa confirmada

1. **Rack/Torre vazio + `equipment/` chamado duas vezes**: o clique no
   marker chamava `manageContainer()` (renderer legado, lista antiga),
   que fazia sua própria chamada `equipment/` e abria
   `#container-dialog`. Essa mudança de atributo disparava um
   `MutationObserver` em `map-master-suite.js`, que chamava
   `enhanceContainer()` — uma SEGUNDA chamada `equipment/` +
   `container-layout-v3/`, desenhando o Canvas numa aba que nem estava
   ativa por padrão (a aba "Equipamentos" antiga é que abria primeiro).
2. **Chamadas stale ao abrir CTO/CDO**: o mesmo observer reagia a
   qualquer mutação de atributo em `#container-dialog`, mesmo quando a
   interação atual era sobre uma CTO/CDO (que usa `showUnifilar()`,
   nunca toca nesse dialog) — sobra de uma abertura anterior de
   Rack/Torre na mesma sessão de página.
3. **"2" nos clusters / dois ícones**: `canonicalElementFeatures()`
   deduplicava markers por `tipo+nome+coordenada`, mantendo sempre o
   MENOR ID — cego a se aquele ID tinha equipamentos/layout de
   verdade. Os dados reais do banco (fornecidos pelo Adrian) confirmam
   que os pontos testados (RACK TESTE 01, REP_TORRE_PREFEITURA_IMBAU,
   CTO/CDO TESTE 01) têm exatamente 1 `NetworkElement` cada — então essa
   função nunca deveria estar escondendo nada nesses casos específicos;
   mesmo assim, o critério "menor ID vence" era uma bomba-relógio pra
   qualquer duplicidade real futura, e por isso foi removida.
4. **Dois menus no botão direito**: `marker.on("contextmenu", ...)` só
   cortava a propagação do evento nativo DEPOIS de checar
   `editing && unifiedEditor && window.mapV0758?.openElementMenu` — se
   qualquer uma dessas condições fosse falsa no momento do clique, a
   função retornava sem parar o evento, que então vazava pro menu global
   "Adicionar ao mapa" (`map-v074-ui.js`).

## Entrega

- **`static/js/map-master-suite.js`**:
  - novo `openContainerWorkspace(id)` — função pública única pra abrir
    Rack/Torre: 1 chamada `equipment/`, 1 chamada `container-layout-v3/`,
    renderiza o Canvas, só então mostra o dialog;
  - `MutationObserver` de `#container-dialog` removido; carregamento de
    dado agora é sempre por chamada de função explícita;
  - guarda de geração (`state.container.openGeneration`) contra
    resposta atrasada sobrescrever o editor de um elemento diferente;
  - `close` do dialog agora limpa `dataset.elementId`/estado temporário
    e avança a geração, sem disparar novo carregamento;
  - aba "Canvas 2D" é a ativa por padrão (era "Equipamentos").
- **`static/js/map-editor.js`**:
  - dedup de markers agora só por ID real repetido na mesma resposta
    da API (nunca por nome/tipo/coordenada) — `canonicalElementFeatures()`
    removida;
  - registro central `state.elementMarkers` (1 entrada por ID real,
    nunca duas no mesmo layer);
  - clique/menu de Rack/Torre chamam `openContainerWorkspace()`
    (delega pro Canvas) em vez do `manageContainer()` legado;
  - `marker.on("contextmenu", ...)` corta a propagação do evento
    ANTES de qualquer checagem — nunca mais vaza pro menu global.
- **`static/js/map-v074-ui.js`**: segunda camada de proteção — o menu
  global ignora cliques sobre `.leaflet-marker-icon`,
  `.leaflet-interactive`, `.map-element-marker` e qualquer elemento
  com `data-element-id`.
- **`static/js/map-v0758-core-ui.js`**: `window.mapV0758` criado vazio
  (`window.mapV0758 = window.mapV0758 || {}`) já na primeira linha
  executável do arquivo; a atribuição final virou `Object.assign` em
  vez de substituir o objeto. Um erro de inicialização mais adiante no
  arquivo não deixa mais o objeto inteiro `undefined`.
- **`templates/map.html`**: marcador de cache `-tower-r13` → `-tower-r14`
  nos 5 assets ligados a este hotfix (além do `MAP_VERSION` em si, que
  já muda a query string sozinho).

## Fora de escopo / preservado

- Nenhum arquivo de backend (`apps/network_map/api/views.py` não foi
  tocado) — os dados e respostas da API já estavam corretos, a causa
  era 100% de orquestração no frontend.
- `map-v0757-field-usability.js`/`.css` continuam removidos.
- Nenhuma migration criada ou alterada.
- Nenhum dado excluído ou alterado no banco.
- `manageContainer()` legado continua existindo (usado só como refresh
  interno de formulários já ocultos pela nova UI — `.master-legacy-hidden`
  — não é mais chamado ao abrir Rack/Torre do zero).

## Validação executada neste sandbox (sem GDAL/Postgres/Node)

- `python -m compileall -q apps config tests`.
- `python -m unittest discover -s tests -p "test_map_v0750_static.py" -v`.
- `git diff --check` / `git diff --cached --check`.
- `node --check` indisponível neste ambiente (Node.js não instalado) —
  limitação conhecida, registrada, não simulada.
- `python manage.py check` indisponível por falta de GDAL — limitação
  conhecida, registrada, não simulada.

## Homologação pendente no Debian (antes da tag)

1. abrir RACK TESTE 01 (ID 9106) — deve mostrar DIO 01 (equipamento 49),
   restaurar `positions`/`cablePositions`, mostrar o cabo de saída;
2. abrir REP_TORRE_PREFEITURA_IMBAU (ID 9102) — deve mostrar os 5
   equipamentos, restaurar `notes`/`positions`, mostrar os 2 cabos de
   entrada;
3. confirmar no Network do DevTools: só 1 chamada `equipment/` e 1
   `container-layout-v3/` ao abrir Rack/Torre;
4. abrir CTO TESTE 01 e CDO TESTE 01 — confirmar que NÃO disparam
   `equipment/`/`container-layout-v3/`, só `elements/<id>/`, `layout/`,
   `splices/`;
5. botão direito sobre marker (Rack/Torre/CTO/CDO) — só o menu do
   elemento abre, nunca o menu global junto;
6. botão direito em área vazia do mapa — só "Adicionar ao mapa" abre;
7. mover um ponto e cancelar — confirma que a posição volta exata;
8. observar Console/Network por 60s sem loop de requisição nem exceção.

A tag `map-v0.75.9` só será criada depois dessa homologação real.
