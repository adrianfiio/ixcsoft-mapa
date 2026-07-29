# Changelog

Todas as mudanças relevantes do projeto são registradas neste arquivo.

## [Não lançado]

### Planejado

- Integrar as telas de equipamentos ao novo layout compartilhado
- Implementar coleta SNMP real em OLTs FiberHome
- Criar perfis de OIDs por modelo e firmware
- Implementar descoberta de portas PON e ONUs

## [0.9.4] - 2026-07-29

### Corrigido

- Clique diretamente sobre o cabo agora registra a reserva técnica
- Fibras e tubos já existentes são remapeados para suas posições ABNT; não é necessário excluir cabos

### Adicionado

- Configuração de quantidade de bandejas na CEO
- Splitters opcionais por bandeja com proporção configurável
- Visualização unifilar inicial das bandejas, fusões e splitters da CEO

## [0.10.0] - 2026-07-29

### Adicionado

- Edição de metragem, posição e exclusão de reservas técnicas
- Conversão de uma reserva existente em CTO ou CEO
- Inserção direta de CTO/CEO no meio de um cabo
- Divisão automática do cabo em dois trechos ligados ao novo elemento
- Editor unifilar da CEO com fibras dos cabos conectados
- Criação de fusões por arrastar uma fibra sobre outra e escolha da bandeja
- Remoção de fusões no próprio unifilar

## [0.10.1] - 2026-07-29

### Corrigido

- Fusões não exibem mais IDs internos como “Fibra 122 → Fibra 134”
- Identificação agora usa cabo, número operacional e cor da fibra

### Alterado

- Unifilar da CEO redesenhado como grafo óptico com cabos, portas, bandejas e linhas coloridas
- Ligações podem ser feitas clicando em duas portas ou arrastando uma fibra sobre outra

## [0.10.2] - 2026-07-29

### Adicionado

- Splitters aparecem dentro de suas respectivas bandejas no grafo
- Porta de entrada e portas de saída numeradas para cada splitter
- Ligação de fibra do cabo à entrada do splitter
- Ligação das saídas do splitter às fibras dos cabos derivados
- Linhas específicas para alimentação e derivações

### Alterado

- Popup do unifilar ampliado para até 96% da tela e área de desenho expandida

## [0.10.3] - 2026-07-29

### Corrigido

- Inicialização bloqueada pelo `admin.E040` após adicionar portas de splitter
- Busca automática do painel administrativo agora encontra splitters por bandeja, CEO, nome e código

## [0.11.0] - 2026-07-29

### Adicionado

- Cabos e bandejas podem ser arrastados livremente no canvas unifilar
- Posições do desenho são persistidas por CEO
- Inclusão, alteração e exclusão individual de splitters em cada bandeja
- Remoção de ligações das entradas e saídas dos splitters
- Cadastro de OLT diretamente no mapa
- Seleção da OLT de origem e animação do caminho da luz nos cabos
- Destaque visual da direção origem → destino da rede

## [0.12.3] - 2026-07-29

### Adicionado

- Expansão individual e persistente para mostrar todas as fibras de cada cabo.
- Controles inferiores para agrupar ou separar PPPoE e equipamentos.

### Alterado

- Satélite sem API e sem cobrança definido como mapa inicial.
- Camadas simplificadas para clientes PPPoE online e offline.
- Painel duplicado de fusões removido do rodapé do unifilar.

## [0.12.2] - 2026-07-29

### Adicionado

- Zoom persistente no unifilar com ampliar, reduzir e ajustar à tela.
- Atalhos de cabo, CTO, CEO, OLT e nomes no menu recolhido.
- Linhas bicolores para representar fusões entre fibras de cores diferentes.

### Alterado

- Janela do unifilar ampliada para praticamente toda a tela.
- Splitter vertical com entrada à esquerda e saídas empilhadas à direita.
- Saídas do splitter fazem transição da cor de entrada para a fibra de destino.

## [0.12.1] - 2026-07-29

### Adicionado

- CTOs agora possuem o mesmo editor unifilar das CEOs.
- Passagem direta permite continuar fibras para o próximo cabo na CTO.
- Splitters da CTO aceitam entrada e derivações para fibras de outros cabos.

### Alterado

- Splitters são exibidos verticalmente, com entrada superior e saídas inferiores.
- A seta luminosa acompanha o ângulo real de cada trecho do cabo.
- CTOs existentes recebem a estrutura óptica automaticamente.

## [0.12.0] - 2026-07-29

### Adicionado

- Desenho de cabos iniciando e terminando diretamente em OLT, CEO ou CTO.
- Controle para mostrar ou ocultar nomes dos cabos e equipamentos.
- Seleção simplificada de cabo pela quantidade de fibras.

### Alterado

- O fluxo luminoso só atravessa uma CEO quando existe fusão real no unifilar.
- Cabos de entrada são posicionados à esquerda e cabos de saída à direita no unifilar.
- O modelo selecionado define automaticamente a quantidade de fibras e sugere um nome padronizado.

## [0.11.2] - 2026-07-29

### Corrigido

- Linhas de fusão e de splitter agora podem ser clicadas para excluir e redesenhar.
- Ligações usam a cor ABNT da fibra de origem e, após o splitter, da fibra de destino.
- Fluxo óptico no mapa ganhou seta luminosa animada indicando o sentido.
- Marcadores de CTO, CEO e OLT agora possuem ícones próprios e identificação legível.

## [0.11.1] - 2026-07-29

### Corrigido

- Uma fibra não pode mais participar de duas ligações simultâneas
- Ligações duplicadas existentes são limpas automaticamente pela migração
- Bandejas não são mais repetidas abaixo do canvas

### Adicionado

- Partículas luminosas animadas sobre o cabo mostram o deslocamento do sinal
- Bandeja selecionada diretamente no canvas para receber a fusão
- Linhas curvas, retas ou ortogonais com preferência persistente
- Exclusão de fusão clicando diretamente na linha do desenho

## [0.9.3] - 2026-07-29

### Adicionado

- Edição do traçado por vértices arrastáveis diretamente no mapa
- Encaixe automático das pontas em CTOs, CEOs e demais elementos próximos
- Reserva técnica posicionada no mapa com metragem identificada
- Símbolo próprio de bobina para reservas
- Sequência de cores ABNT: verde, amarelo, branco, azul, vermelho, violeta, marrom, rosa, preto, cinza, laranja e água

### Alterado

- Catálogos ópticos existentes são migrados para a ordem ABNT

## [0.9.2] - 2026-07-29

### Adicionado

- Seleção do cabo conectado e da fibra que alimenta o splitter ao editar a CTO
- Vínculo persistente entre cabo, fibra, CTO e entrada do splitter
- Exibição do nome do cabo, número e cor real da fibra no unifilar
- Atualização automática do estado e da contagem de fibras utilizadas

## [0.9.1] - 2026-07-29

### Adicionado

- Edição de postes, CTOs, CEOs e cabos diretamente pelos pop-ups do mapa
- Conexão da origem e do destino do cabo aos elementos do mesmo projeto
- Encaixe automático das pontas do cabo e acompanhamento ao mover o elemento
- Configuração de capacidade, proporção do splitter e portas ao criar ou editar CTO
- Cadastro persistente de splitters e portas de atendimento
- Visualização unifilar de cada CTO com o estado individual das portas
- Exclusão de cabos diretamente no mapa

## [0.9.0] - 2026-07-29

### Adicionado

- Projetos de rede com nome, código, status, empresa e cor
- Projeto obrigatório para novos elementos e cabos
- Menu do mapa recolhível e redimensionável
- Camadas independentes de estrutura, clientes online, offline e sem estado
- Cadastro de postes, CTOs e CEOs clicando diretamente no mapa
- Movimentação de elementos por arrastar e soltar
- Desenho de cabos por múltiplos pontos
- Importação de arquivos KML e KMZ para o projeto selecionado
- Alternância entre mapa convencional e imagem de satélite
- Resumos de elementos, cabos, rotas e clientes

### Segurança

- Criação, alteração, importação e exclusão exigem usuário autenticado
- Endpoints de leitura permanecem disponíveis para o mapa operacional

## [0.8.9] - 2026-07-29

### Corrigido

- Logo centralizada no eixo visual do menu lateral
- Favicon local permitido sem bloquear o comando `apply`

## [0.8.8] - 2026-07-29

### Adicionado

- Camada de satélite sem API paga no mapa operacional
- Seletor entre mapa convencional e imagem de satélite
- Referência ao favicon `afservice-map-favicon.png`

### Alterado

- Removidos todos os textos exibidos abaixo da logo

## [0.8.7] - 2026-07-29

### Corrigido

- Alinhamento visual do subtítulo sob a logo em todas as interfaces
- Remoção do título duplicado acima do cartão de login

## [0.8.6] - 2026-07-29

### Alterado

- Cabeçalhos simplificados para exibir somente a logo oficial
- Subtítulo atualizado para “Mapa e operação de rede”
- Login administrativo redesenhado com interface moderna e responsiva
- Textos da visão geral preparados para redes ópticas e wireless

## [0.8.5] - 2026-07-29

### Alterado

- Produto renomeado de IXCSoft Mapa para AFService Map
- Logotipo oficial aplicado no dashboard, mapa e Django Admin
- Arquivos estáticos movidos para `/assets/static/`

### Corrigido

- Estilos do Django Admin servidos corretamente atrás do Nginx
- `apply` agora valida dashboard, Admin e logotipo

## [0.8.4] - 2026-07-29

### Adicionado

- Navegação de retorno do mapa operacional para o dashboard

## [0.8.3] - 2026-07-29

### Corrigido

- CSS principal servido por uma rota que não é interceptada pelo Nginx
- `apply` agora valida o CSS antes de informar sucesso
- Removido o prefixo duplicado na versão exibida pela interface

## [0.8.2] - 2026-07-29

### Corrigido

- Comando `apply` liberado para servidores administrados como `root`
- Remoção segura do `--remove-orphans` para preservar PostgreSQL e Redis
- Arquivos estáticos deixaram de ser ocultados por um volume Docker
- Versão do deploy passou a acompanhar automaticamente a tag do Git

## [0.8.1] - 2026-07-29

### Adicionado

- Comando global `apply` para atualização automatizada no Debian
- Relatório de deploy com versão, commits, duração e estado dos serviços
- Verificação automática do health check após cada atualização

## [0.8.0] - 2026-07-29

### Adicionado

- Dashboard operacional com indicadores reais de acessos, infraestrutura,
  clientes, OLTs, ONUs e alertas
- Layout base responsivo com navegação para os módulos principais
- Página própria para o mapa operacional em `/mapa/`
- Resumo da última sincronização com o IXCSoft

### Alterado

- Página inicial restaurada como visão geral da operação
- Mapa deixou de ocupar temporariamente a rota inicial

## [0.7.0] - 2026-07-29

### Adicionado

- Estrutura multiempresa
- Dashboard inicial de visão geral
- Modelos de POP, rack e equipamentos
- Modelos de infraestrutura óptica
- Modelos de cabo, tubos, fibras e padrões de cores
- Bandejas e fusões ópticas
- Editor GIS e cadastro de elementos da rede
- Base do mapa Leaflet com OpenStreetMap
- Agrupamento de marcadores no mapa
- Busca de clientes, logins, CTOs e ONUs
- Filtros de acessos online, offline e desconhecidos
- Resumo dos acessos exibidos
- API GeoJSON para os pontos de acesso
- Rotas web para cadastro de equipamentos
- Arquivo `.env.example` revisado

### Alterado

- Página inicial passou a exibir o mapa operacional
- Identidade padrão atualizada para IXCSoft Mapa
- Versão padrão da aplicação atualizada para `0.7.0`
- Documentação atualizada para refletir o estado real do projeto
- Documentação do IXCSoft ampliada para incluir provisionamentos FTTH

### Observações

- A página do mapa substituiu temporariamente o dashboard inicial.
- A reconstrução do dashboard, usando um layout base e uma rota separada para o
  mapa, será feita no próximo ciclo do frontend.
- A estrutura dos coletores SNMP existe, mas a coleta real ainda não está
  concluída.

## [0.6.2] - 2026-07-28

### Corrigido

- Compose de produção adaptado para PostgreSQL e Redis externos
- Serviços web, worker e beat separados
- Domínio direcionado ao serviço web na porta interna 8000

## [0.6.1] - 2026-07-28

### Adicionado

- Variável `WEB_URL`
- Derivação de host permitido, CSRF e CORS a partir da URL pública
- Opção `DJANGO_SECURE_SSL_REDIRECT`

## [0.6.0] - 2026-07-28

### Adicionado

- Deploy com Docker e Gunicorn
- Modos web, worker e beat
- Health checks de liveness e readiness
- Configuração para proxy HTTPS e EasyPanel

### Corrigido

- Worker e Beat deixaram de executar migrations concorrentes
- Versão da API centralizada em `APP_VERSION`

## [0.5.1] - 2026-07-28

### Alterado

- README transformado em documentação permanente
- Histórico de atualizações movido para o Changelog

## [0.5.0] - 2026-07-28

### Adicionado

- Sincronização de `radpop_radio_cliente_fibra`
- Modelo de provisionamento FTTH
- Campos de projeto, CTO, PON, ONU, VLAN e sinal óptico
- Associação inicial entre login, CTO e ONU
- Endpoint `/api/ixc/fiber-assignments/`
- Operações HTTP no cliente IXCSoft

### Alterado

- Cliente compatível com URL raiz e `/webservice/v1`
- Listagem ajustada ao padrão do WebserviceClient do IXCSoft

## [0.4.0] - 2026-07-28

### Adicionado

- Criptografia de tokens com Fernet
- Testes do cliente HTTP
- Testes de criptografia
- Migrations iniciais

## [0.3.0] - 2026-07-28

### Adicionado

- Arquitetura em camadas
- Cliente HTTP do IXCSoft
- Serviços, repositórios e tarefas Celery
- Base dos coletores FiberHome
- GitHub Actions

## [0.2.0] - 2026-07-28

### Adicionado

- Modelos de OLT, PON, ONU e histórico óptico
- Modelos de CTO, rotas, cabos e elementos
- Clientes e logins IXCSoft
- Regras, eventos e notificações de alerta
- API REST inicial

## [0.1.0] - 2026-07-28

### Adicionado

- Estrutura inicial Django
- Docker Compose
- PostgreSQL/PostGIS
- Redis e Celery
- Swagger
- Health check
