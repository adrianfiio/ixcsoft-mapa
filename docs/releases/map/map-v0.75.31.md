# MAP v0.75.31 — CTO, CEO e CDO no editor 2D do Rack/Torre

## Objetivo

Levar o padrão de editor já usado por Rack/Torre para as três caixas ópticas: CTO, CEO e CDO. A v0.75.30 já fazia isso somente para CTO; esta release completa o escopo para CEO/CDO, que são armazenadas como `NetworkElement.ElementType.SPLICE_BOX`.

## Arquitetura

- O shell/janela é o mesmo `openContainerWorkspace`/`map-master-suite.js` usado por Rack e Torre.
- O domínio óptico continua isolado em `map-cto-suite.js`: splitters, cabos, notas, fusões, drag e zoom.
- O Canvas óptico fica embutido no painel comum por `map-v0758-core-ui.js`; não abre `#unifilar-dialog` por cima da janela nova.
- Rack e Torre mantêm seus fluxos atuais.

## Identidade

O backend envia `container.subtype` a partir de `metadata.import_subtype`. O frontend apresenta `CEO`, `CDO` ou `CEO/CDO` quando o subtipo não estiver definido, sem mascarar a caixa como Torre.

## Endpoints liberados para splice_box

1. `container_equipment` — bootstrap do shell comum.
2. `container_port_links` — coerência das operações do shell.
3. `container_layout_v3` — persistência das posições do Canvas.
4. `create_passive_endpoint_v3` — coerência da API do shell.
5. `import_container_device_type_yaml` — evita chave ausente e mantém o contrato comum.

A UI de CTO/CEO/CDO continua escondendo equipamento genérico, inventário e matriz; as liberações de backend servem ao motor compartilhado e evitam respostas 404/KeyError durante o bootstrap.

## Testes

- Contrato estático novo em `tests/test_map_v07531_contract.py`.
- Versão central atualizada em `tests/test_map_v0750_static.py`.
- O aplicador também executa verificação sintática própria antes de concluir.

## Banco de dados

Sem migrations.
