# MAP v0.75.21 — CTO/CDO: barra de atalhos, 100% aditiva

## Objetivo

Continuar a paridade visual da CTO/CDO/CEO com o Rack/Torre (item já em
andamento desde a v0.75.20), com uma restrição clara combinada com o
usuário: só adicionar, nunca remover ou renomear nada que já existe.

## Descoberta que mudou o plano original

Investigação da área de toolbar/zoom antes de reescrevê-la encontrou que
`.unifilar-zoom` e `.optical-links` (o SVG das linhas) são manipulados em
sequência por **5 scripts decoradores diferentes**, cada um com
suposições próprias sobre a estrutura exata:

- `map-fusion-polish.js` → `modernToolbar()`: substitui **inteiramente**
  o `innerHTML` de `.unifilar-zoom` por um slider de zoom próprio
  (`data-fusion-zoom`), e marca o elemento com a classe `.fusion-toolbar`.
- `map-optical-editor-v2.js` → `installRouteToolbar()`/`decorateSvg()`:
  procura `.fusion-toolbar` ou `.unifilar-zoom` para colar um editor de
  rota manual, e mantém seu **próprio** sistema de pontos de dobra
  (`manual_link_routes_v2`) sobre os mesmos `<path>` do `.optical-links`.
- `map-optical-editor-v3.js` → `compactFusionToolbar()`: mesma busca
  `.fusion-toolbar || .unifilar-zoom`, injeta um botão "Cabos".
- `map-v0750-tower-workspace.js`/`map-v0758-core-ui.js`: aplicam classes
  de compactação/fullscreen sobre `.ceo-instructions`.

Reescrever essa área sem poder testar visualmente cada passo teria risco
real de quebrar algum desses scripts silenciosamente. Diante disso, a
decisão (tomada com o usuário) foi: continuar em modo **estritamente
aditivo** — nunca remover ou renomear uma classe/ID que esses scripts já
procuram.

## O que foi feito

- Nova barra `.tower-workspace-toolbar-v0750` inserida **antes** da barra
  de instruções antiga (`.ceo-instructions`), que continua 100% intacta
  (mesmo texto, mesmos IDs, mesma estrutura).
- Botões "+ Splitter" e "+ Nota" na barra nova chamam exatamente os
  mesmos manipuladores já existentes do menu de contexto (clique com
  botão direito no fundo do Canvas) — calculando um ponto central da área
  visível como posição padrão do novo item.
- Nenhuma classe ou ID removido, renomeado ou reestruturado.

## Verificação de segurança

Com essa abordagem, os 5 scripts decoradores continuam encontrando
exatamente os elementos que esperavam, sem qualquer alteração de
comportamento.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhuma classe/ID pré-existente removida ou renomeada.
