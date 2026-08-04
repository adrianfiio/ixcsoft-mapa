# MAP v0.75.16 — rota se auto-ajusta ao mover, linha acende no hover

## Objetivo

Corrigir a queixa central do feedback mais recente: mover um equipamento
(ex.: OLT) deixava as ligações "travadas" na rota antiga, voltando a
cortar por cima de outro equipamento/porta.

## Causa raiz

Duas rotinas de roteamento coexistem no mesmo Canvas: a base
(`map-master-suite.js`, `drawContainerLinks`/`orthogonalPath`) atualiza a
linha em tempo real durante o arraste (sem desvio de obstáculo), e a
camada v0.75.12+ (`map-v07512-links-ptp.js`, `rewriteLinks`/`autoRoute`,
com todo o desvio de obstáculo construído desde a v0.75.13) só
recalcula quando algo dispara explicitamente esse recálculo — hoje,
apenas em alguns eventos específicos (abrir o container, redimensionar o
Canvas). Nenhum dos dois avisava o outro quando um arraste terminava, e
uma rota manual (ponto de dobra arrastado à mão) é uma coordenada absoluta
fixa: se o equipamento dono da ligação se move, a rota manual não
acompanha e passa a cortar por cima de outra coisa.

## Corrigido

- Novo evento `map:node-moved`, disparado ao final de qualquer arraste
  (equipamento, cabo, ou a nova alça de redimensionar da OLT).
- `map-v07512-links-ptp.js` escuta esse evento: para os links que tocam o
  item movido, apaga a rota manual salva (se houver) e recalcula do zero
  com o roteador com desvio de obstáculo, persistindo o resultado.
- Efeito prático: mover a OLT (ou qualquer equipamento/cabo) faz as linhas
  ligadas a ela se reajustarem sozinhas, em vez de ficar presas na forma
  antiga.

## Adicionado

- Passar o mouse sobre uma linha de ligação (cordão ou fusão) acende
  (glow) a linha inteira — ajuda a seguir o caminho exato quando várias
  linhas cruzam o Canvas.

## Investigado, aguardando mais informação do usuário

### DIO "porta já em uso"

Revisão completa de `container_port_links` (validação de conflito de
porta): a checagem já distingue corretamente frente (cordão,
`source_port__isnull=False`) de trás (fusão, `cable_fiber__isnull=False`)
no MESMO port ID — não há dependência da orientação visual
esquerda/direita trocada na v0.75.14. Não encontrei nenhum outro trecho
do código com suposição de posição antiga (grep em todo o projeto por
`dio-rear`/`dio-front` só retorna a própria definição). **Preciso de um
passo a passo exato** (qual cabo, qual porta, em qual DIO) pra reproduzir
e confirmar se é um bug real ou uma tentativa legítima de reconectar uma
porta já ocupada.

### PTP — erro 500

Ainda sem o traceback do servidor pedido na v0.75.15
(`docker logs ixcsoft-mapa-web-1 --tail 100` no momento do erro). Sem ele
não é seguro avançar.

### Roteamento pela "canaleta" entre placas + CTO/CDO/CEO com Canvas próprio

O usuário confirmou que ambos os pedidos (rotear como no HTML de
referência do Gemini, usando as calhas/canaletas entre placas como
caminho; e dar à CTO/CDO/CEO uma versão do Canvas de Rack/Torre restrita
a splitter padrão + cabos) fazem parte da mesma frente de trabalho da
"Organização Rack" 44U já combinada para uma entrega dedicada — não
tentado nesta versão.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
