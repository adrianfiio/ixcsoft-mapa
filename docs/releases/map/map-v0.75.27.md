# MAP v0.75.27 — CTO/CDO/CEO: janela idêntica à do Rack/Torre

## Objetivo

Feedback direto do usuário depois da v0.75.26 (que só extraiu o código
pra um arquivo próprio, sem mudar o visual): "o modo que ta as
CTO,CEO E CDO esta ruim... quero que seja iguais da torre... você só
alterou não copiou todo formato... como eu disse copia tudo que e
torre faz... como abre a janela tudo, não só a interna, quero
IDENTICO DA TORRE."

## Diagnóstico

Comparando o CSS da janela da Torre (`#container-dialog.tower-workspace-dialog-v0750`,
em `map-v0750-tower-workspace.css`) com o da CTO/CDO/CEO
(`#unifilar-dialog.map-v0758-optical-workspace`, em
`map-v0758-core-ui.css`), achei diferenças reais na **moldura da
janela em si**, não só no conteúdo de dentro:

| Propriedade | Torre | CTO/CDO/CEO (antes) |
|---|---|---|
| `border-left` | `rgba(56, 189, 248, .2)` | `#203b52` (cor diferente) |
| `box-shadow` | `-18px 0 55px rgba(0,0,0,.38)` | nenhuma |
| `z-index` | `1800` | não definido (usa o padrão do navegador) |
| `::backdrop` | transparente, sem blur | não definido |
| Offset com sidebar recolhida | `72px` (ou `54px` minimizada) | `66px` (não tratava "minimizada") |
| Cabeçalho | **escondido** — só a barra de ferramentas customizada aparece | **visível** — cabeçalho nativo ("Fusões · NOME" + X) MAIS a barra de ferramentas customizada por baixo, duas barras empilhadas |

O item do cabeçalho duplicado era provavelmente a diferença mais
visível de todas: a Torre mostra UMA barra no topo (a customizada, com
título+ações+fechar); a CTO/CDO/CEO mostrava DUAS (o cabeçalho nativo
do `<dialog>` do navegador, com seu próprio título e X, e por baixo a
barra de ferramentas feita na v0.75.23).

## O que mudou

- `static/css/map-v0758-core-ui.css`: bloco `MAP_V07527_CTO_WINDOW_PARITY`
  — `border-left`, `box-shadow`, `z-index` e `::backdrop` da janela da
  CTO/CDO/CEO agora usam os **mesmos valores literais** copiados do
  CSS da Torre (não reinventados, copiados). Offset da sidebar
  recolhida/minimizada corrigido pra bater exatamente (72px/54px).
- **Cabeçalho nativo escondido só para CTO/CDO/CEO**: nova classe
  `map-cto-suite-active-v07527`, ligada em `showUnifilar()`
  (`map-editor.js`) só quando `element.splice_box` existe (ou seja,
  só CTO/CDO/CEO — nunca pro Rack, que reaproveita o mesmo diálogo
  `#unifilar-dialog` pra outra finalidade, a fusão de DIO/cabo, e
  continua precisando do cabeçalho nativo dela).
- `static/js/map-cto-suite.js`: a barra de ferramentas ganhou seu
  próprio botão de fechar, mesma classe (`.tower-workspace-close-v0758`)
  e mesmo ícone SVG que a Torre usa, já que o cabeçalho nativo (que
  tinha o X de antes) agora fica escondido.

## O que NÃO foi mudado (diferença que sobra, não é visual)

A Torre abre sua janela com `dialog.show()` (não-modal — o resto da
página continua clicável por trás) enquanto a CTO/CDO/CEO usa
`dialog.showModal()` (modal — trava foco, bloqueia clique fora). Essa
é uma diferença de **comportamento de interação**, não de aparência —
mudar isso tem risco real (foco de teclado, tecla Esc, clique fora)
que prefiro não arriscar sem poder testar ao vivo. Se isso também
incomodar visualmente/funcionalmente, é a próxima coisa a ajustar.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- **Nenhum arquivo do Rack/Torre alterado** — só copiei os VALORES do
  CSS dele pro CSS da CTO, não editei o arquivo da Torre.
- Rack (fusão de DIO/cabo) e o fallback continuam com o cabeçalho
  nativo normal, sem nenhuma mudança de comportamento pra eles.
