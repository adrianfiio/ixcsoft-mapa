# MAP v0.75.20 — CTO/CDO: primeira fatia do sistema próprio (visual)

## Objetivo

Ponto 3 do feedback mais recente: CTO/CDO/CEO ainda abre "o editor antigo",
não igual ao Rack/Torre. Decisão de arquitetura tomada com o usuário
antes de escrever qualquer código (ver "Nota sobre o caminho escolhido").

## Decisão de arquitetura

Duas opções concretas foram apresentadas:

1. **Sistema próprio, mesmo visual** (escolhida): construir a experiência
   da CTO/CDO isolada do código que o Rack/Torre usa hoje, ligada nos
   dados de splitter/fibra que já existem e já funcionam
   (`/splices/`, `/splitters/`, `/layout/`). Risco: baixo — se algo sair
   errado, só afeta a tela da CTO, nada quebra no Rack/Torre.
2. Reaproveitar literalmente `#container-dialog`/`openContainerWorkspace`
   fingindo splitter como `ContainerEquipment`. Descartada: exigiria
   mexer no código de backend que o Rack/Torre usa **agora em produção**,
   com risco real de quebrar os dois sistemas juntos se a tradução de
   dados saísse errada.

## O que foi feito nesta fatia

- Nós de splitter (`.graph-splitter-node`) e cabo (`.fiber-cable-node`)
  do editor de fusões (`#unifilar-dialog` — nunca usado pelo Rack/Torre)
  ganharam as classes `master-canvas-node`/`master-node-port` do Canvas
  2D, por cima das classes que já existiam. Mesma borda, sombra, raio,
  cor de fundo e formato de porta em pílula do Rack/Torre.
- Porta do splitter em uso (fibra de saída ligada, ou cascata) fica com
  destaque verde, igual ao padrão de porta "used" do Canvas 2D.
- A largura fixa padrão do `master-canvas-node` (245px) foi neutralizada
  pra esses nós — um splitter com muitas saídas (ex.: 1:16) precisa de
  mais espaço do que isso; a largura natural desses componentes
  (existente desde a v0.75.14) foi preservada.
- **Nenhuma lógica de clique-para-ligar, arraste, zoom (v0.75.18) ou
  persistência foi tocada** — é herança visual pura, por cima do que já
  funciona.

## O que ainda falta pra paridade completa

- Painel/toolbar idêntico ao `.tower-workspace-toolbar-v0750` (hoje o
  editor de fusões tem seu próprio cabeçalho de instruções).
- Aba "Canvas 2D" explícita como no Rack/Torre (hoje é uma view única).
- Botão "+ Equipamento" não se aplica aqui (por design: só splitter e
  cabo, conforme pedido do usuário), mas o "+ Adicionar splitter" pode
  ganhar o mesmo estilo de menu do "+ Adicionar" do Rack/Torre.
- Motor de roteamento de linha com desvio de obstáculo (construído pra
  Rack/Torre entre v0.75.13-16) ainda não portado — o editor de fusões
  usa seu próprio desenho de linha SVG mais simples.

Cada um desses vai virar sua própria fatia testável, como sempre.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhum arquivo usado pelo Rack/Torre (`map-master-suite.js`,
  `map-v0750-tower-workspace.js`) foi tocado nesta versão — só
  `map-editor.js` (função `showUnifilar`, exclusiva de CTO/CDO/CEO) e CSS
  aditivo.
