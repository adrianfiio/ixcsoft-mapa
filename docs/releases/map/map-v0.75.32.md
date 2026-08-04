# MAP v0.75.32 — sessão estável do Canvas óptico

## Problema reproduzido

Depois de abrir uma CTO/CEO/CDO uma vez, a segunda abertura podia falhar em
`redrawOpticalLinks()` porque o código procurava `#connection-style` no
`document`. O elemento pertencia ao DOM de uma renderização anterior e já
podia ter sido removido. A mesma arquitetura acumulava listeners no modo
embutido e não cancelava fetches/renders atrasados.

## Solução

- Sessão exclusiva por renderização (`createSession`, `dispose`, geração).
- Todos os listeners relevantes registrados com cleanup central.
- Consultas de controles de estilo e zoom limitadas ao `content` atual.
- Guardas de sessão ativa antes de redesenhar ou concluir carregamentos.
- Geração no shell para ignorar resposta atrasada ao fechar/trocar de caixa.
- Encerramento explícito no evento `close` do `#container-dialog`.
- Estado de carregamento/erro dentro do próprio Canvas.
- Contador da CTO separa portas de atendimento de saídas fusionadas.

## Compatibilidade

O conteúdo técnico continua sendo cabos, fibras, fusões, splitters, notas,
zoom, pan e posições persistidas. Rack e Torre não mudam. Sem migrations e
sem endpoint novo.
