# MAP v0.75.14 — PTP, DIO e fusões (correções sobre feedback real da v0.75.13)

## Objetivo

Corrigir 4 problemas apontados após uso real da v0.75.13: alça do fio grande
demais, enlace PTP não abrindo, orientação do DIO invertida no Canvas 2D, e
esclarecer o estado real do editor de fusões de CTO/CDO/CEO.

## Alça de dobra do fio

- Bolinha visual volta a 6px de raio (era 13px na v0.75.13).
- Clique/arraste agora usa um círculo invisível de 14px de raio por cima da
  bolinha, só para receber o clique — visualmente pequena, funcionalmente
  fácil de acertar.

## Enlace PTP

Causa raiz real, confirmada por leitura do código de criação de
equipamento: `_generate_container_equipment_ports()` (backend) já gerava
portas padrão para OLT, ONU, PTO e DIO — mas **não para Rádio PTP nem Access
Point**. Um rádio recém-criado ficava sem nenhuma porta; clicar "Ligar
PTP?" não tinha porta wireless nenhuma pra reconhecer, então nada
acontecia.

- Rádio PTP e Access Point agora nascem com uma porta wireless padrão.
- Quando não há torre/rádio de destino disponível no projeto, o aviso deixa
  de ser um toast (fácil de não perceber) e passa a ser um diálogo modal
  explicando a causa.

## Orientação do DIO

O DIO no Canvas 2D tinha a porta "frente" (cordão pro equipamento) fixada à
direita e a "traseira" (fusão com o cabo) à esquerda — invertido do
esperado. Trocado para: esquerda = frente/equipamento, direita =
traseira/cabo, tanto no layout de bandeja compacta (grid ≥24 portas) quanto
no layout simples. O roteamento automático do cordão OLT→DIO deixou de
assumir sempre um canal à direita — agora escolhe o lado mais perto de onde
a porta de destino realmente está.

## Fusões de CTO/CDO/CEO

Investigação encontrou que o editor de fusões (`#unifilar-dialog` →
`.optical-graph`) **já é** um sistema de nós arrastáveis com clique-para-
ligar completo: cabo, splitter (entrada/saída/cascata) e remoção de
ligação — não é um formulário antigo nem uma tela estática. A aparência
visual foi atualizada para a mesma linguagem do Canvas 2D de Rack/Torre
(cores, raio de borda, sombra dos cartões), sem tocar em nenhuma lógica de
clique, arraste ou conexão.

**Pendente de confirmação com o usuário**: se o pedido original era sobre
uma capacidade que genuinamente não existe hoje — por exemplo, vincular
diretamente um cliente/assinante (`AccessPoint`) a uma porta de saída do
splitter dentro deste editor (`SpliceTraySplitterPort` não tem esse campo
hoje; a ligação com cliente hoje acontece via cabo DROP até um PTO/ONU em
outro ponto do mapa) — isso é uma funcionalidade nova, não uma correção
visual, e precisa de escopo próprio.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhuma alteração nos endpoints `/splices/`, `/splitters/`, `/layout/` da
  CTO/CDO — apenas CSS.
- `_generate_container_equipment_ports()` ganhou um novo `elif` (PTP/Access
  Point); nenhum branch existente (OLT/ONU/PTO/DIO) foi alterado.
