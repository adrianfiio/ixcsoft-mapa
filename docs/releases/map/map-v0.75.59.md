# MAP v0.75.59

Hotfix pequeno: o texto "Auto fusão" do botão na matriz de fusão do DIO
não estava aparecendo — só o ícone do raio ficava visível.

## O que mudou

`[data-dio-auto-fuse-v07538] span` ganhou `display: inline !important;
color: #fff !important;` explícito. O `<span>Auto fusão</span>` já
existia no HTML e o botão já tinha `color:#fff`, mas o texto não estava
renderizando de verdade — reforçado direto no `<span>` pra garantir.

## Validação

- `tests/test_map_v07559_contract.py` (novo, 2 testes).
- Suíte histórica completa — zero regressões novas.
- Validação real no navegador (Playwright, ambiente Docker isolado):
  screenshot confirma "Auto fusão" em branco, nítido, ao lado do raio
  azul.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.

## Outros itens reportados nesta rodada (investigados, sem correção de
código ainda — ver relatório completo na conversa)

- **409 no console da matriz de fusão**: investigado — não é bug, é o
  backend rejeitando corretamente porta/fibra já usada. Não corrigido
  porque não há nada errado para corrigir; a melhoria possível é uma
  mensagem mais amigável em vez do erro cru no console.
- **Cordão visual OLT↔DIO ao ligar a frente**: testado ao vivo, o
  cordão SVG renderiza corretamente conectando os dois nós. Não
  reproduzido — precisa de mais detalhe/print do caso real.
- **Portas do Switch empilhadas na Torre**: testado ao vivo (Torre
  isolada e também Rack→Torre na mesma sessão) — grid de 12 colunas
  lado a lado em ambos os casos, não reproduzido.
- **Linha azul do Rack vazando pra Torre**: testado Rack→Torre na
  mesma sessão — nenhum artefato residual encontrado. Encontrado,
  porém, um vazamento real e diferente no código (classe
  `tower-workspace-dialog-v0750` nunca é removida do dialog
  reaproveitado) — candidato a causa raiz de vazamentos de contexto
  entre Rack/Torre em geral, mas não é o mecanismo exato do "risco
  azul" relatado; fica para investigação futura com mais detalhe.
- **Matriz de fusão: fibras do cabo não aparecem como 12 lado a lado**,
  **duplo clique pra "Remover fusão"**, **organizador de cabo entre
  uplink/serviço no Switch**: não iniciados nesta rodada — ver relatório
  na conversa.
