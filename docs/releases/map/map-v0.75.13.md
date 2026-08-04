# MAP v0.75.13 — usabilidade do Canvas (rotas, notas, alças, OLT uplink)

## Objetivo

Corrigir problemas de usabilidade reportados após homologação real da v0.75.11/v0.75.12
no editor Canvas de Rack/Torre, sem mexer em API, modelo de dados ou fluxo de
abertura do workspace.

## Notas do Canvas

- Causa raiz encontrada: `.master-canvas-nodes` (pai direto da nota) é
  `pointer-events: none`; cada nó de equipamento reabre a exceção em CSS
  próprio, mas a nota nunca tinha essa regra — em um navegador real, clique e
  arraste passavam direto pela nota sem nunca alcançá-la, apesar do
  JavaScript de arraste/editar/excluir já estar correto desde a v0.75.11.
- Corrigido com uma única regra CSS (`pointer-events: auto` em
  `.master-canvas-note`). Nenhuma lógica de estado foi alterada.

## Roteamento de ligações

- "Organizar equipamentos" e novas ligações sem ponto manual usavam uma
  coordenada de meio-caminho fixa entre origem e destino, sem considerar o
  que estava no meio do caminho — por isso linhas cortavam por cima de
  outros equipamentos depois de organizar o Canvas.
- Novo comportamento: antes de traçar o segmento do meio, o roteador mede as
  caixas **realmente renderizadas** (via `getBoundingClientRect`) de todo
  equipamento, cabo e nota no Canvas e procura o nível livre mais próximo do
  preferido. Se não houver obstáculo no caminho, o resultado é idêntico ao
  de antes — layouts já organizados não mudam.
- O roteamento especial OLT → DIO (canal lateral abaixo da placa) não foi
  alterado.

## Alça de dobra do fio

- Raio de clique da alça (o ponto do meio que pode ser arrastado) aumentado
  de 8px para 13px.
- O sistema de alças mais antigo (que desenhava um segundo círculo por cima
  do mesmo ponto, ativo só durante "Editar linhas") foi desligado — ele
  ficava "fantasma" no lugar antigo depois de um arraste pelo sistema novo,
  que é quem realmente processa clique/arraste/exclusão hoje.

## Torre

- Botão "Fibras" (destaque de fibra do DIO) deixa de aparecer no editor da
  Torre — é específico do Rack. Continua disponível no Rack sem alteração.
- Terminação DIO frente (cordão)/traseira (fusão) já era genérica pra
  Rack e Torre desde a v0.75.12 (`container_port_links` não filtra por tipo
  de container) — confirmado, nenhuma mudança necessária aqui.
- Enlace PTP (clique na porta Wireless → escolher torre e rádio de destino)
  já estava implementado ponta a ponta desde a v0.75.12 — confirmado,
  nenhuma mudança necessária aqui.

## Atualizar sem recarregar

- Novo botão "Atualizar" no toolbar do Rack/Torre, ao lado de "Editar
  linhas"/"Fibras". Chama a mesma rotina pública já usada para (re)abrir o
  workspace (`mapMasterSuite.openContainerWorkspace`), recarregando
  equipamentos/cabos/layout sem fechar o dialog nem recarregar a página.

## OLT — placa de uplink

- O editor de portas genérico ("Adicionar interfaces compatíveis") excluía
  totalmente equipamentos do tipo OLT — só era possível adicionar placas
  PON pelo fluxo dedicado, e a única forma de ganhar uma porta de uplink era
  importar um YAML de Device Type.
- Agora a OLT tem sua própria lista restrita nesse editor genérico
  (RJ45/SFP/SFP+ de gerência ou uplink + alimentação), mantendo PON
  exclusivamente no fluxo de placas por slot — não duplica o caminho.

## Explicitamente fora do escopo desta versão

Itens pedidos na mesma leva, mas não incluídos aqui por serem mudanças de
arquitetura maiores demais pra entrar sem homologação visual real no meio do
processo:

- **Unificar CTO/CDO só no Canvas 2D novo**: hoje CTO/CDO/CEO usam
  exclusivamente o modal `#unifilar-dialog` (fusões/splitters), sem nenhum
  Canvas 2D próprio — o Canvas atual (`openContainerWorkspace`) só existe
  para `rack`/`tower`. Migrar CTO/CDO pra lá exige um novo renderizador
  (o modelo de dados de CTO é `CTOSplitter`/`SpliceTray`/`FiberSplice`, bem
  diferente de `ContainerEquipment`/`ContainerEquipmentPort` usado por
  Rack/Torre), não uma adaptação pequena.
- **"Organização Rack" (visão 44U estilo simulador de patch panel)**: pedido
  explícito de usar dados reais do banco. Viável (o layout hoje já é um JSON
  livre em `NetworkElement.metadata`, dá pra guardar uma segunda visão sem
  migration), mas é um renderizador inteiro novo, do tamanho de qualquer uma
  das versões anteriores sozinho — fica pra uma entrega própria.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhuma mudança no fluxo `openContainerWorkspace`/`dialog.show()`.
