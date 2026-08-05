# MAP v0.75.34 — workspace óptico isolado

Data: 2026-08-04

## Objetivo

Reativar a edição visual de CTO, CEO e CDO sem reutilizar o diálogo, o DOM ou o estado do Canvas de Rack/Torre.

## Arquitetura

O frontend óptico passa a existir em módulos próprios:

- `static/js/optical/optical-api.js`: chamadas HTTP e contratos da API;
- `static/js/optical/optical-state.js`: sessão, seleção, layout e descarte;
- `static/js/optical/optical-renderer.js`: renderização Canvas 2D e interação espacial;
- `static/js/optical/optical-workspace.js`: shell, painéis, eventos e ciclo de vida;
- `static/css/map-optical-workspace-v07534.css`: estilo integralmente prefixado.

Cada abertura cria uma raiz `.ixc-optical-workspace` nova. O fechamento aborta requisições, desconecta o `ResizeObserver`, remove a raiz e descarta o estado. Nenhum desses módulos usa `#map-master-container`, `#container-dialog`, `#unifilar-dialog` ou `openContainerWorkspace`.

## Funcionalidades

- visualização de cabos, fibras, bandejas, fusões e splitters;
- criação, edição e exclusão segura de bandejas;
- criação e exclusão de fusões;
- criação, alteração de relação e exclusão de splitters;
- ligação e desligamento de entrada e saídas de splitter, inclusive cascata entre splitters;
- associação manual de cabos próximos;
- notas e posições persistidas no layout da caixa;
- portas de atendimento da CTO exibidas separadamente das saídas ópticas;
- zoom, pan, enquadramento e movimentação de nós.

## Backend

As APIs ópticas existentes continuam sendo a fonte de dados. A release adiciona apenas o CRUD de bandejas e reforça a autorização de escrita nas APIs de fusões, layout e splitters.

Não há migration.

## Compatibilidade

Rack e Torre continuam no fluxo existente e não recebem alteração em seus arquivos de Canvas. CTO, CEO e CDO chamam `window.IXCOpticalWorkspace.open(id)` pelo clique normal e pelo menu de contexto.

## Validação obrigatória antes do merge

Abrir e fechar repetidamente CTO, CEO e CDO, alternar entre caixas e Rack/Torre sem atualizar a página, editar todos os tipos de ligação e confirmar console sem erros ou promises rejeitadas.
