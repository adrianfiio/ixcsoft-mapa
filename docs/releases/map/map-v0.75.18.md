# MAP v0.75.18 — CTO/CDO/CEO: zoom e pan iguais ao Canvas do Rack/Torre

## Objetivo

Primeira fatia real (não adiada) da paridade de uso pedida entre o editor
de fusões da CTO/CDO/CEO e o Canvas 2D de Rack/Torre.

## O que já era igual (confirmado por leitura de código, sem mudança)

- Nós arrastáveis (cabo, splitter) com posição persistida.
- Clique-para-ligar: fibra → porta de entrada do splitter, porta de saída
  do splitter → fibra, cascata de splitter, fusão direta fibra-a-fibra.
- Menu de contexto do fundo só oferece "+ Adicionar splitter" e
  "+ Adicionar nota" — **nunca existiu opção de adicionar equipamento
  arbitrário**. O pedido de "não aceitar equipamentos, só splitter padrão"
  já era o comportamento real antes desta versão.
- Aparência visual (cores, raio de borda, sombra dos cartões) já alinhada
  ao Canvas 2D desde a v0.75.14.

## Adicionado nesta versão

- **Zoom com Ctrl+roda do mouse**: mesmo gesto do Canvas 2D. Usa a mesma
  variável de zoom (`layout.zoom`) e os mesmos botões +/-/Ajustar já
  existentes — só adiciona outro jeito de disparar o mesmo zoom.
- **Pan arrastando o fundo**: clicar e arrastar uma área vazia do editor
  de fusões move a visão (como arrastar o Canvas do Rack/Torre), em vez de
  depender só da barra de rolagem. Clicar em um nó, porta ou botão
  continua funcionando normalmente — só o fundo vazio arrasta.

## Fora desta fatia

Ainda não portado: o motor de roteamento de linha OTIMIZADO (que evita
equipamento no caminho, construído para Rack/Torre entre as v0.75.13 e
v0.75.16) — o editor de fusões usa seu próprio desenho de linha SVG mais
simples. Avaliar se vale a pena unificar os dois motores é uma decisão de
arquitetura maior, não uma correção pontual.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhuma mudança na lógica de conexão/splitter/fusão existente.
