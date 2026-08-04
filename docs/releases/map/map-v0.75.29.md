# MAP v0.75.29 — CTO sem equipamento genérico + splitter/nota/fusões/portas

## Objetivo

Usuário confirmou a v0.75.28 funcionando ("Pronto agora sim tá como eu
queria") — CTO abrindo o motor real do Rack/Torre. Pedido de
continuação, direto: "vamos agora tirar as funções de rack daí, ok?
Tire tudo que for equipamento e adicione pra fazer as fusões aí e
adicionar splitter, nota, e já aparecer 1 widget da quantidade de
porta que a CTO aceita para ligar nela os clientes e DROPs."

## O que mudou

### Removido da CTO (só dela)

- Botão **"+ Adicionar"** (equipamento genérico — OLT, DIO, switch,
  etc.) — a CTO não tem esse conceito.
- Botão **"Ligar portas"** (cordão entre portas de equipamento).
- Botão **"Editar linhas"** (edição de conexão de equipamento).
- Itens do menu Ferramentas: **"Inventário"** e **"Relatório de
  ligações"** (equipamento genérico).

Rack e Torre continuam com tudo isso normalmente — os toggles checam
`identity.type === "cto"` e são reavaliados a cada abertura, nunca
aditivos.

### Adicionado na CTO

- **"+ Splitter"** e **"+ Nota"** na barra de ferramentas principal —
  clicar abre o editor de fusões (`map-cto-suite.js`, o mesmo usado
  desde a v0.75.26) e já dispara a mesma ação que os botões internos
  dele usam. Reaproveitado via simulação de clique
  (`document.querySelector('[data-ceo-quick-add="${action}"]')?.click()`),
  não duplicado.
- **Botão "Fibras" renomeado pra "Fusões"** no contexto da CTO (já
  abria o editor de fusões desde a v0.75.28 — só o rótulo mudou, pra
  ficar mais claro que ali é onde as fusões acontecem).
- **Widget de portas**: mostra `usadas/capacidade` (ex.: "3/16 portas
  (clientes/DROPs)") na barra de ferramentas — `capacidade` vem de
  `element.cto.capacity`, `usadas` conta as saídas de splitter já
  ligadas a uma fibra.
- Estado vazio do Canvas (quando a CTO não tem equipamento — sempre,
  já que ela não usa esse conceito) ganhou botões próprios: "+
  Splitter", "+ Nota", "Abrir Fusões".

## Bug real encontrado e corrigido (efeito colateral positivo)

Durante a implementação, notei que `.tower-workspace-actions-v0750
button` e `.tower-popover-v0750 button` têm `display: inline-flex`
**sem** `!important`. O atributo `hidden` do HTML é implementado pelo
navegador via a regra `[hidden] { display: none }` no user-agent
stylesheet — e estilos de **autor** sempre vencem estilos de
**user-agent**, independente de especificidade. Ou seja, o filtro que
**já existia** de tipos de equipamento permitidos por rack/tower
(`button.hidden = !allowed.has(...)`, da v0.75.10) pode nunca ter
escondido esses botões visualmente de verdade.

Corrigido com uma regra defensiva:
```css
.tower-workspace-actions-v0750 [hidden],
.tower-popover-v0750 [hidden] {
    display: none !important;
}
```
Isso beneficia tanto os toggles novos da CTO quanto o filtro antigo de
equipamento — sem risco, porque só afeta elementos que já tinham o
atributo `hidden` (o comportamento correto pra eles sempre foi ficar
escondidos).

## Como a regra "sem URL de API crua" foi respeitada

`map-v0758-core-ui.js` tem uma regra arquitetural já garantida por
teste (`test_map_v0750_static.py`): esse arquivo nunca deve ter uma
URL de API (`/api/map/...`) escrita literalmente nele — só
`map-editor.js` é dono de rotas de API, os outros arquivos usam
helpers expostos via `window.networkMap`. O widget de portas precisa
buscar `element.cto.capacity`/splitters, então foi adicionado
`window.networkMap.fetchElement(id)` (novo helper em `map-editor.js`,
reaproveitando a mesma função `api()` que `showUnifilar()` já usa) —
`map-v0758-core-ui.js` chama esse helper, nunca a URL diretamente.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API novo — o widget reaproveita `GET
  /api/map/elements/<id>/`, já existente.
- Nenhuma mudança de comportamento pro Rack/Torre.
