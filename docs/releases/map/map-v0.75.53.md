# MAP v0.75.53

Hotfix crítico: depois de abrir e fechar um Rack, abrir uma CTO, CDO ou
CEO travava em "Carregando..." com `Cannot read properties of undefined
(reading '0')`.

## Contexto

O Adrian reportou a sequência exata: abrir o editor do mapa → abrir um
Rack → fechar o Rack → tentar abrir uma CTO/CDO/CEO → a janela fica em
"Carregando..." e mostra "Não foi possível abrir a caixa." + o erro
JavaScript acima.

**Limitação honesta deste ambiente**: não há navegador, Playwright nem
Selenium disponíveis neste sandbox (verificado antes de começar), nem
banco Postgres/GDAL pra levantar o servidor com dados reais. Não foi
possível reproduzir ao vivo nem capturar um stack trace real do
navegador. Toda a investigação abaixo foi feita por leitura de código —
rastreando a cadeia de chamadas de verdade, função por função, até
confirmar por lógica onde o comportamento diverge do esperado — não por
suposição. O método é o mesmo já usado nesta sessão para achar bugs
igualmente não-óbvios sem navegador (o bug de parênteses no `{% if %}`
do Django, o mismatch de nome de atributo `V07537`/`V07538` no DIO), mas
**não é equivalente a uma reprodução real**, e isso precisa ser validado
no servidor antes de confiar cegamente no relatório.

## Investigação

CTO, CDO e CEO usam um runtime completamente isolado desde a v0.75.34
(`window.IXCOpticalWorkspace`, em `static/js/optical/*.js`), que nunca
acessa `#container-dialog` nem `#map-master-container` (confirmado lendo
o arquivo inteiro — `document.body.appendChild(root)` é o único ponto de
inserção no DOM). A leitura completa de `optical-workspace.js`,
`optical-state.js`, `optical-api.js` e `optical-renderer.js` (mais de
1900 linhas ao todo) não encontrou nenhum acesso `[0]` desprotegido
alcançável a partir de `IXCOpticalWorkspace.open()` — todos já usavam
`?.`/`|| []` corretamente.

A investigação então seguiu pro lado do Rack, porque a sequência exata
relatada (Rack → fechar → caixa óptica) é o dado mais forte disponível.
Achado confirmado, não hipotético:

- `static/js/map-rack-physical-v07542.js` adiciona a classe
  `"v07542-physical-rack"` em `#map-master-container` ao renderizar um
  Rack (`applyPhysicalRack`), e só a **remove** dentro de `enhance()`,
  que exige `dialog?.open === true` pra fazer qualquer coisa
  (`if (!root || !dialog?.open) return;`). Ou seja: `resetPhysicalMode()`
  só roda quando o usuário troca pra Torre **com o dialog ainda aberto**
  — fechar o dialog diretamente nunca dispara esse reset.
- **Toda** reimplementação de `isRack()` carregada no template
  (`map-rack-viewport-v07546.js`, `map-rack-ux-v07547.js`,
  `map-rack-integrity-v07548.js`, `map-rack-maintenance-v07552.js`)
  prioriza exatamente essa classe: `if (root.classList.contains(
  "v07542-physical-rack")) return true;` — antes até de olhar qualquer
  outro dado.
- `#container-dialog` também guarda `dataset.containerType = "rack"`,
  setado por `map-v0758-core-ui.js::updateContainerIdentity()` a cada
  `map:container-rendered`, e igualmente nunca resetado no fechamento —
  segunda fonte independente do mesmo problema, já que `isRack()` também
  cai nesse dataset como fallback.

Resultado: depois de abrir um Rack pela primeira vez numa sessão de
página, **todo runtime do Rack passa a acreditar que o Rack continua
aberto para sempre**, mesmo interagindo depois com qualquer outro
elemento — a garantia de isolamento da v0.75.34 ("CTO/CEO/CDO usam um
runtime próprio... sem acessar... qualquer estado de Rack/Torre") fica
comprometida na prática, porque o lado do Rack nunca larga os
marcadores que o identificam como tal.

Isso bate exatamente com a causa-raiz que a própria tarefa já
suspeitava (seção 3 do prompt, "ciclo de vida do Rack"), e é a explicação
mais concreta e verificável que a leitura de código permitiu confirmar
para a sequência relatada. **Não foi possível confirmar com um stack
trace real que esta é a única causa** — é a conclusão de maior confiança
que a investigação estática permitiu chegar.

## Correção

### `static/js/map-rack-physical-v07542.js`
Nova função `teardownRackModeOnClose()`, registrada uma única vez em
`#container-dialog.addEventListener("close", ...)` dentro de `init()`.
Ao fechar o dialog (por qualquer via — `.close()`, tecla Escape, botão
de fechar):
- remove `"v07542-physical-rack"` e os artefatos DOM do Rack físico
  (via `resetPhysicalMode`, já existente, só passou a ser alcançável
  também no fechamento);
- limpa `dialog.dataset.containerType`/`elementType`;
- reseta `state.currentKind` para `"unknown"`;
- incrementa `state.enhanceGeneration` — o mesmo mecanismo de geração já
  usado por `schedule()`/`enhance()` pra descartar resposta atrasada,
  agora também invalida qualquer `await` em voo no momento do fechamento.

### `static/js/map-editor.js`
`editElement()` acessava `element.cto.splitters[0]` sem checar se
`splitters` era de fato um array — uma CTO recém-criada, sem splitter
cadastrado ainda, tinha esse campo ausente (não vazio) em alguns casos,
e o acesso direto quebrava com exatamente "Cannot read properties of
undefined (reading '0')". Corrigido com `Array.isArray(...)` antes do
acesso. Esse caminho é o menu de contexto "Editar informações", não o
fluxo relatado — corrigido por ser um defeito real e confirmado
encontrado durante a varredura, não por ser a causa do bug relatado.

### `static/js/optical/optical-state.js`
`hydrate()` agora normaliza `session.optical` e `session.cableState`
(`normalizeOptical`/`normalizeCableState`) garantindo `cables`/
`splices`/`splitter_links` sempre como array, mesmo se o backend
devolver um payload parcial. Reforço defensivo — a leitura de código não
encontrou um caso concreto em que isso quebrasse hoje, mas essa é
exatamente a garantia pedida explicitamente pra qualquer estado vazio
das caixas.

## Revalidação dos itens da v0.75.52 (por código, não navegador)

Reconferido que o código atual ainda implementa corretamente, sem
regressão introduzida por este hotfix:
- Switch 8/12/16 portas numa linha (`is-single-row` + `repeat(var(
  --port-count), ...)`).
- Pan com botão esquerdo preservando zoom (`event.button !== 0`,
  threshold de movimento antes de ativar arraste).
- Slots de uplink únicos no topo da OLT (`face.insertBefore(bank,
  serviceSlots)`).
- Troca de posição de equipamentos ao arrastar (`swapCandidate`,
  `is-swap-target-v07552`).
- Pares do DIO frente/traseira (`pair.appendChild(front); pair.
  appendChild(rear);`, `order: 1`/`order: 2` no CSS).

Nenhum defeito estático encontrado nesses cinco pontos. Não há como
confirmar, sem navegador, se o comportamento relatado como "ainda não
funcionando" persiste — é possível que parte dessa percepção viesse da
mesma contaminação de estado do Rack corrigida acima (interagir com um
segundo elemento sem recarregar a página, com o Rack "preso" em modo
ativo, produz comportamento inconsistente em qualquer um desses cinco
pontos).

## Fora de escopo / limitações

- Nenhuma migration.
- Nenhum dado (porta, ligação, splitter, layout) apagado.
- Testes Playwright/Selenium reais **não foram escritos nem executados**
  — não há navegador neste ambiente para rodá-los ou validá-los, e
  escrever testes que nunca rodaram criaria uma falsa sensação de
  cobertura. Os testes entregues são do mesmo estilo usado em toda a
  MAP desde a v0.75.34: asserções estruturais sobre o texto-fonte dos
  arquivos (`tests/test_map_v07553_contract.py`).

## Validação executada neste sandbox (sem GDAL/Postgres/navegador)

- `python -m py_compile` nos arquivos Python tocados (nenhum neste
  hotfix — só JS).
- Balanceamento manual de chaves/parênteses/colchetes nos 3 arquivos JS
  tocados (substituto de `node --check`, ausente neste ambiente — **não
  equivalente** a checagem real de sintaxe JS).
- `python -m unittest tests.test_map_v07553_contract -v`.
- `git diff --check`.
- `python manage.py check` / `test` / `makemigrations --check` —
  executados, falham identicamente com `ImproperlyConfigured: Could not
  find the GDAL library` (limitação conhecida deste ambiente, não
  relacionada a este hotfix).
- Suíte histórica completa como verificação extra de que nada regrediu.
- Revisão manual do diff: nenhuma migration, `PLATFORM_VERSION`
  inalterada.

## Pendente — precisa ser feito no servidor, com navegador real

1. Reproduzir exatamente a sequência do bug (Rack → fechar → CTO/CDO/CEO,
   inclusive vários ciclos) e confirmar ausência do erro.
2. Confirmar visualmente os cinco itens revalidados por código (Switch,
   pan, uplinks, troca de posição, DIO).
3. Console e aba Network sem erros/loops durante toda a sequência.
