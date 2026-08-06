# MAP v0.75.50

## Estabilização crítica do Rack

A v0.75.49 podia entrar em ciclo de renderização ao observar alterações do próprio painel de uplinks. Cada nova renderização iniciava outra consulta HTTP, que alterava o DOM e acionava novamente o mesmo fluxo. Em sessões reais isso resultava em centenas de chamadas repetidas, `ERR_INSUFFICIENT_RESOURCES`, Rack travado e OLT sem edição.

### Correções

- Consultas de uplink agora usam cache de 30 segundos.
- Uma chamada já em andamento é compartilhada por todos os consumidores.
- Falhas entram em cooldown de 5 segundos e não derrubam o restante do Rack.
- O render do painel de uplink usa assinatura de conteúdo e não recria DOM sem mudança real.
- O `MutationObserver` ignora elementos gerados pela própria atualização.
- O ciclo de melhoria do Rack é debounced e executado em voo único.
- Foram removidas as chamadas extras de 180 ms e 520 ms que repetiam o mesmo trabalho.
- O fluxo físico não chama mais `refresh()` recursivamente.
- A organização automática possui intervalo de proteção contra repetição.
- O DIO é consultado somente uma vez por instância renderizada.

## Compatibilidade

- O endpoint `/api/map/v07549/.../uplinks/` é mantido.
- Nenhuma migration foi adicionada.
- Nenhum dado de OLT, placa, uplink, DIO ou Rack é removido.
- O CSS visual da v0.75.49 continua sendo utilizado.
