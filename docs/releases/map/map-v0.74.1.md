# map-v0.74.1 — Polimento visual final do mapa

Release exclusiva do componente **Mapa**, baseada na `main` pós-PR #56:

```text
66180d30988527321813764e6a04a783e1797459
```

A plataforma permanece em `platform-v0.77.0`.

## Corrigido

- Rack/Torre passa a usar uma barra superior única, com botões e ícones alinhados;
- Canvas 2D abre enquadrado, sem barras desnecessárias quando há poucos equipamentos;
- Canvas recebe zoom `+`, `−`, `Ajustar` e `Ctrl + scroll`;
- menu lateral recolhido deixa de exibir mensagens soltas entre os ícones;
- barras horizontal e vertical visíveis do menu lateral são removidas;
- botão fixo de cancelar é ocultado quando a faixa contextual de desenho já possui `Concluir/Cancelar`;
- faixa de desenho deixa de ficar sobreposta à toolbar principal;
- ficha técnica organiza metadados aninhados em cards fluidos, sem texto vertical e sem scroll dentro de scroll;
- estado de implantação passa a integrar o grid da ficha técnica.

## Segurança e isolamento

- nenhuma migration;
- nenhuma alteração em Financeiro, Dashboard ou Superadmin;
- nenhum equipamento, cabo, fibra, fusão ou histórico apagado;
- `PLATFORM_VERSION=0.77.0` preservada;
- `MAP_VERSION=0.74.1`.

## Homologação obrigatória antes da tag

- abrir Rack/Torre e confirmar toolbar com ícones;
- abrir Canvas 2D com um e vários equipamentos;
- testar `+`, `−`, `Ajustar` e `Ctrl + scroll`;
- confirmar ausência de barras visíveis no menu lateral e no Canvas quando desnecessárias;
- desenhar cabo e confirmar apenas uma ação de cancelamento;
- abrir ficha técnica e conferir metadados longos, impressão/PDF e estado de implantação;
- DevTools → Network por 60 segundos: uma chamada `equipment/` e uma `container-layout-v3/` por abertura, sem repetição automática.

Tag futura, somente após homologação:

```text
map-v0.74.1
```
