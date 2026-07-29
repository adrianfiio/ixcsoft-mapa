# Changelog

Todas as mudanças relevantes do projeto são registradas neste arquivo.

## [Não lançado]

### Planejado

- Integrar as telas de equipamentos ao novo layout compartilhado
- Implementar coleta SNMP real em OLTs FiberHome
- Criar perfis de OIDs por modelo e firmware
- Implementar descoberta de portas PON e ONUs

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
