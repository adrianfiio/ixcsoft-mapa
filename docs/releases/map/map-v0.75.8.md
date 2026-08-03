# MAP v0.75.8 — Hotfix do editor unificado

**Data:** 2026-08-03
**Base obrigatória:** `58d59dc490d91158e530743beb112be2856a46ae`
**Plataforma preservada:** `0.82.0`
**Mapa:** `0.75.8`

## Motivo

A homologação real da MAP v0.75.7 revelou sobreposição entre o runtime principal e o arquivo complementar `map-v0757-field-usability.js`. O resultado observado foi: menus e labels sobrepostos, clique em CTO sem abrir as fusões, botão direito vazando para o menu global, chamadas repetidas e abertura de um registro duplicado vazio no lugar da estrutura já configurada.

## Correção estrutural

- remove do carregamento o runtime e o CSS complementares da v0.75.7;
- mantém somente os renderizadores oficiais de mapa, Canvas e fusões;
- adiciona um módulo auxiliar v0.75.8 limitado a diálogos, identidade visual e menu contextual — ele não carrega dados, não renderiza marcadores e não observa/reabre workspaces;
- volta a abrir o workspace óptico com `showModal()`, impedindo clique e menu do mapa por trás;
- mantém confirmação de movimentação, notas multilinha, direção óptica sugerida, cabos laterais e coordenadas negativas;
- preserva a criação idempotente e as regras próprias de Rack já incorporadas no backend;
- agrupa visualmente registros idênticos em um único marcador, mantendo todos os IDs disponíveis no resolvedor manual e sem apagar automaticamente;
- acrescenta um resolvedor manual para registros sobrepostos: mostra os IDs e nunca apaga automaticamente.

## Regras funcionais

- Rack: OLT, DIO, Switch, Router, Firewall, Servidor, PTO e Outros. AP, PTP e ONU/ONT são bloqueados também no backend.
- Torre: equipamentos de campo compatíveis e DIO limitado a 24 portas.
- Clique esquerdo: Rack/Torre abrem o editor técnico; CTO/CEO/CDO abrem fusões.
- Botão direito no elemento: editar, abrir, resolver duplicados e excluir o ID selecionado.
- Botão direito no fundo do mapa: permanece reservado para “Adicionar ao mapa”.
- Notas: `textarea`, múltiplas linhas, edição, exclusão e movimentação.
- Canvas e fusões: posições negativas e ajuste global.

## Homologação obrigatória

1. confirmar apenas um renderer e uma barra por estrutura;
2. clicar em CTO/CEO/CDO e abrir fusões;
3. usar botão direito no elemento sem abrir o menu global;
4. resolver os dois IDs sobrepostos, mantendo o registro que contém equipamentos/fusões;
5. abrir a Torre e o Rack mantidos e confirmar seus dados existentes;
6. mover um ponto, cancelar e confirmar retorno exato; repetir salvando;
7. criar, editar, mover e excluir nota longa;
8. testar cabos dos dois lados e sugestão de inversão;
9. observar Console e Network por 60 segundos sem loops;
10. executar `manage.py check`, testes Python, `node --check` e `git diff --check`.

## Tag futura

Criar somente depois da homologação no Debian:

```text
map-v0.75.8
```
