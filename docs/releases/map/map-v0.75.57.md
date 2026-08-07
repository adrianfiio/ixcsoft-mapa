# MAP v0.75.57

Hotfix: portas do Switch/Router/Firewall/Server criados pela Torre,
"Editar rota" mesclado no menu de cabo certo, empilhamento real das
portas do DIO e ícone no botão "Auto fusão". A partir de novo relato
direto do Adrian usando o editor, com screenshots.

## 1. Switch criado pela Torre não deixava adicionar portas

**Causa raiz**: existem dois caminhos de criação de equipamento — o
diálogo próprio do Rack (`equipment_collection_v07539`, já gerava
portas certo) e o diálogo genérico "+ Equipamento" da Torre
(`container_equipment`), que nunca gerava nenhuma porta pra
Switch/Router/Firewall/Server. Um Switch criado pela Torre ficava com 0
portas reais, e o editor de portas mostrava "Da porta 1 até 1" (mínimo
de segurança da UI), sem deixar adicionar mais nada.

**Correção**: `_generate_container_equipment_ports` (`views.py`) ganhou
um branch pra esses 4 tipos (24 portas padrão pra Switch, 8 pra
Router/Firewall/Server); o diálogo da Torre ganhou o campo "Quantidade
de portas" (4/8/12/16/24/48), enviado como `port_count` e salvo em
`metadata`.

## 2. "Editar rota" não aparecia no menu de cabo

Na rodada anterior (v0.75.56) o botão foi adicionado a um sistema de
menu de cabo criado à parte (`map-editor.js`), que nunca vencia
visualmente porque outro sistema, mais antigo e já existente
(`map-v07539-suite.js`), sempre desenhava por cima — o real, que o
usuário sempre viu, nunca teve o botão novo.

**Correção**: sistema duplicado removido de `map-editor.js` (mantendo só
o clique esquerdo sem popup, que continua correto), e "Editar rota"
mesclado no menu real de `map-v07539-suite.js`, entre "Editar cabo" e
"Alterar sentido".

## 3. Portas do DIO ainda lado a lado (não 12 pares empilhados)

A tentativa da v0.75.56 não teve efeito visual nenhum. Duas causas
raiz, uma escondendo a outra:

1. **Arquivo errado**: três arquivos CSS diferentes definem o grid do
   par (`.v07539-dio-pair`) com `!important` e a mesma especificidade —
   quem vence é sempre o último `<link>` carregado em `templates/map.html`,
   que é `map-rack-runtime-v07552.css`. A tentativa anterior mexeu em
   `map-rack-maintenance-v07549.css`, carregado antes — editou o arquivo
   errado, sem efeito nenhum.
2. **Posicionamento explícito mais antigo**: mesmo corrigindo o grid pro
   arquivo certo (1 coluna, 2 linhas), as portas continuavam lado a
   lado. Causa: `map-v0750-tower-workspace.css` (bem mais antigo) já
   força `.dio-front { grid-column: 1 }` / `.dio-rear { grid-column: 2 }`
   — posicionamento explícito de grid sempre vence auto-placement,
   então o grid de 1 coluna sozinho não bastava; as portas continuavam
   sendo empurradas pra colunas diferentes por aquela regra antiga.

**Correção**: grid do par corrigido em `map-rack-runtime-v07552.css`
(1 coluna, 2 linhas de 26px); `[data-port-role="front"]` e `[data-port-role="rear"]`
ganharam `grid-column: 1 !important` (mesma coluna) com `grid-row`
explícito (1 e 2), sobrescrevendo a regra antiga de coluna. A regra
agora morta em `map-rack-maintenance-v07549.css` foi limpa (só sobrou o
que o arquivo vencedor não define: `border-radius`/`background`), pra
não deixar duas versões conflitantes do mesmo grid espalhadas em dois
arquivos.

## 4. Auto fusão: ícone de raio azul

**Correção**: botão "Auto fusão" (`map-dio-fusion-v07538.js`) ganhou um
SVG de raio azul (`#38bdf8`, com leve brilho) ao lado do texto.

## Investigado, sem correção nesta rodada

- **"Torre mostra linha azul forte, tipo cabo, igual Rack"**: não
  consegui reproduzir com as informações disponíveis (testei abrir
  Torre logo após mexer no Rack, várias sequências). Preciso de um
  screenshot ou passo a passo mais preciso pra investigar direito.
- **Matriz de fusão do DIO "não conta as 12 portas"**: investigado no
  código (consulta do backend e lógica de agrupamento no frontend), sem
  achar uma causa raiz clara nem um limite artificial de 12. Não deu
  pra confirmar nem corrigir com confiança nesta rodada — precisa de
  mais contexto (screenshot da matriz mostrando o problema, ou um cabo
  de teste específico que reproduza).

## Confirmado que já funcionava (nenhuma mudança necessária)

- **Mover equipamento no Rack**: já funciona (arrastar pra um slot
  vazio reposiciona livre; arrastar pra cima de outro troca os dois de
  posição). O que parecia "travado" no relato era clicar em cima dos
  botões do cabeçalho do card (editar/excluir), que corretamente não
  iniciam arraste — arrastando pelo restante do cabeçalho funciona.

## Validação

- `tests/test_map_v07557_contract.py` (novo, 7 testes).
- Suíte histórica completa, rolling-bump dos testes que travam "versão
  atual".
- **Validação real no navegador** (Playwright + Chromium, ambiente Docker
  isolado no servidor com dados sintéticos, produção nunca tocada):
  1. Switch criado pela Torre: campo "Quantidade de portas" visível
     (padrão 24), 24 portas reais criadas e editáveis depois (não mais
     travado em "Da porta 1 até 1").
  2. Menu de cabo real confirmado com "Editar rota" no meio das ações;
     clicar caiu direto no modo de edição tracejado com handles
     arrastáveis.
  3. DIO: `getComputedStyle` do par confirmado com 1 coluna
     (`grid-template-columns: 22px`), frente e trás em `top` diferentes
     (empilhadas) e mesmo `left` (mesma coluna) — confirmado também por
     screenshot, 12 pares compactos, não mais 24 quadrados numa fileira.
  4. Botão "Auto fusão" com o raio azul confirmado por screenshot.
  Ambiente derrubado por completo ao final (containers, volumes,
  imagens, pasta) — nada ficou para trás.

## Fora de escopo

- Layout de portas fiel ao desenho real de cada modelo de equipamento
  (catálogo de modelos conhecidos) — mesma nota da v0.75.56, ainda não
  iniciado.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.
