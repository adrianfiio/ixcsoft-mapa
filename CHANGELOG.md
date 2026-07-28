# Changelog

Todas as mudanças relevantes do projeto serão documentadas neste arquivo.

O formato segue as ideias de Keep a Changelog e o projeto utiliza versionamento
semântico durante o desenvolvimento.

## [Não lançado]

### Planejado

- Coleta SNMP real em OLTs FiberHome
- Perfis de OIDs por modelo e firmware
- Descoberta de portas PON e ONUs
- Migrations iniciais validadas em Docker
- Mapa Leaflet

## [0.5.1] - 2026-07-28

### Corrigido

- README transformado em documentação permanente do sistema
- Histórico de atualizações movido para o CHANGELOG
- Adicionada documentação específica para releases
- Criado template para publicação de releases no GitHub

## [0.5.0] - 2026-07-28

### Adicionado

- Sincronização do endpoint `radpop_radio_cliente_fibra`
- Modelo de provisionamento FTTH
- Campos de projeto, CTO, PON, ONU, VLAN e sinal óptico
- Associação inicial entre login, CTO e ONU
- Endpoint `/api/ixc/fiber-assignments/`
- Operações GET, POST, PUT e DELETE no cliente IXCSoft
- Testes de normalização da URL e listagem via GET

### Alterado

- Cliente IXCSoft compatível com URL raiz e `/webservice/v1`
- Listagem ajustada ao padrão GET do WebserviceClient do IXCSoft

## [0.4.0] - 2026-07-28

### Adicionado

- Criptografia de tokens com Fernet
- Testes do cliente HTTP
- Testes de criptografia
- Estrutura inicial de migrations

### Corrigido

- Registro dos modelos de clientes e logins IXCSoft

## [0.3.0] - 2026-07-28

### Adicionado

- Arquitetura em camadas
- Cliente HTTP inicial do IXCSoft
- Serviços e repositórios
- Tarefas Celery
- Base para coletores FiberHome
- GitHub Actions

## [0.2.0] - 2026-07-28

### Adicionado

- Modelos de OLT, PON, ONU e histórico óptico
- Modelos de CTO, rotas, cabos e elementos de rede
- Clientes e logins IXCSoft
- Regras, eventos e notificações de alerta
- API REST inicial

## [0.1.0] - 2026-07-28

### Adicionado

- Estrutura inicial Django
- Docker Compose
- PostgreSQL/PostGIS
- Redis
- Celery
- Swagger
- Health check
