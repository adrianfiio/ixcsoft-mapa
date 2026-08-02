# Mapa v0.75.0 — Workspace de Torre/Rack no Canvas 2D

Release estrutural da trilha do mapa. O módulo de Rack/Torre passa a abrir diretamente no Canvas 2D, com a criação e o gerenciamento da estrutura concentrados em uma única área de trabalho.

## Principais mudanças

- Canvas 2D aberto diretamente ao entrar em Rack/Torre.
- Toolbar superior com D.I.O, PTO e ativos: AP, PTP, Switch, Router e ONU/ONT.
- Inventário, fibras, matriz e importação YAML abertos em painel lateral, sem trocar a tela principal.
- Painel de propriedades ao clicar em um equipamento, com atalhos para edição, ficha técnica e SNMP.
- Conexões porta a porta diretamente no Canvas.
- Auto-fit e zoom existentes preservados, sem barras visíveis desnecessárias.
- Tela cheia de Rack/Torre e Fusões passa a usar somente CSS, evitando o primeiro clique abrir fora da aplicação.
- Janela de Fusões com toolbar menor e sem barras aninhadas visíveis.
- Importação Device Type YAML protegida contra IP inválido, nome duplicado, excesso de interfaces e conflitos de banco.
- Rack e Torre aceitam DIO, PTO, Router, AP, PTP, Switch e ONU/ONT.

## Limitação SNMP desta rodada

- O painel reutiliza com segurança o perfil SNMP existente (v2c), sem devolver a
  community armazenada em texto puro.
- SNMP v3 exige campos persistentes próprios para usuário, nível de segurança,
  autenticação e privacidade. Como esta release não autoriza migration, esses
  campos não foram simulados nem gravados em metadados inseguros; ficam para uma
  evolução de esquema posterior.

## Segurança e dados

- Nenhuma migration.
- Nenhum equipamento, cabo, fibra ou fusão é removido automaticamente.
- Importação YAML continua transacional: falha completa não deixa equipamento parcial.
- `PLATFORM_VERSION` permanece `0.77.0`.
- `MAP_VERSION` passa a `0.75.0`.

## Homologação obrigatória

- Abrir Rack/Torre e confirmar Canvas 2D direto.
- Testar quick-add de DIO, PTO e cada ativo.
- Testar conexão entre portas.
- Testar painel lateral e propriedades/SNMP.
- Testar tela cheia duas vezes seguidas, sair com ESC e repetir.
- Testar Fusões sem scrolls aninhados visíveis.
- Importar um YAML válido e repetir com o mesmo nome para confirmar erro 409 legível.

## Validação local

- Testes estáticos da release: 10 testes aprovados.
- Validador estrutural, `py_compile`, `compileall` e `git diff --check`: aprovados.
- `node --check` não pôde ser executado porque Node.js não está instalado neste Windows.
- `manage.py check` não pôde inicializar o GeoDjango porque a biblioteca GDAL não está instalada.
- A suíte `pytest` não pôde ser executada porque o módulo `pytest` não está instalado; os testes estáticos também são executáveis diretamente com a biblioteca padrão `unittest`.
