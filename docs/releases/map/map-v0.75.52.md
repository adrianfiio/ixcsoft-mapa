# MAP v0.75.52 — Rack navegável, uplinks funcionais e DIO pareado

## Escopo

- Switches de 8, 12 e 16 portas ficam em uma única linha e se adaptam à largura útil do Rack.
- O Canvas do Rack usa roda apenas para zoom e clique esquerdo segurado para pan em qualquer nível de zoom.
- Slots de uplink aparecem uma única vez, no topo da OLT, e aceitam RJ45, SFP, SFP+, XFP e QSFP+.
- Cada porta de uplink informa nome e velocidade de 1, 10, 25, 40 ou 100 Gbps.
- Equipamentos podem ser arrastados sobre outro equipamento para trocar suas posições em U.
- O DIO mantém cada frente ao lado da respectiva traseira, com 12 pares por cavidade.
- Mantém os nomes e tipos importados por YAML da MAP v0.75.51.

## Compatibilidade

Sem migration. Os perfis de uplink continuam em `v07549_uplink_profiles` e os dados tipados das portas usam `v07551_port_profiles`, preservando os equipamentos existentes.

## Segurança e estabilidade

- escopo por empresa e permissão de edição no backend;
- cache e single-flight de uplinks preservados;
- pan, zoom e hover não fazem requisições;
- o observer ignora o DOM gerado pelo próprio runtime;
- alteração de quantidade de uplinks ligados é bloqueada.
