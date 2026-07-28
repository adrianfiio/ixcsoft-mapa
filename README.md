# IXCSoft Mapa

Plataforma de monitoramento, correlação e visualização geográfica de redes FTTH
integrada ao IXCSoft e a equipamentos GPON.

O objetivo do projeto é reunir informações cadastrais, topologia óptica, estado
das ONUs, potência de sinal, falhas e alertas em uma única aplicação.

## Funcionalidades planejadas

- Integração com a API do IXCSoft
- Sincronização de clientes e logins PPPoE
- Sincronização de projetos, CTOs e provisionamentos FTTH
- Integração SNMP com OLTs FiberHome
- Descoberta de portas PON e ONUs
- Monitoramento de RX, TX, LOS, temperatura e distância
- Correlação entre cliente, login, ONU, CTO e rota óptica
- Mapa interativo com Leaflet e PostGIS
- Importação de arquivos KML e KMZ
- Alertas por Telegram e Zabbix
- Dashboards no Grafana
- Histórico de eventos e sinais ópticos
- API REST documentada com OpenAPI/Swagger

## Arquitetura

```text
IXCSoft API ───────┐
                   ├──> Django API ──> PostgreSQL/PostGIS
FiberHome via SNMP ┘         │
                             ├──> Redis/Celery
                             ├──> Zabbix
                             ├──> Telegram
                             └──> Frontend Leaflet
```

A aplicação é dividida por domínios:

```text
apps/
├── core/
├── ixc_integration/
├── olt_integration/
├── network_map/
└── alerts/
```

Cada integração possui camadas próprias para API, clientes externos, serviços,
repositórios e tarefas assíncronas.

## Tecnologias

- Python
- Django
- Django REST Framework
- PostgreSQL
- PostGIS
- Redis
- Celery
- Docker
- Leaflet
- Zabbix
- Grafana

## Estado do projeto

O projeto está em desenvolvimento ativo. A integração inicial com o IXCSoft já
possui estrutura para sincronizar:

- clientes;
- logins PPPoE;
- provisionamentos do endpoint `radpop_radio_cliente_fibra`.

A coleta SNMP das OLTs e o frontend geográfico ainda serão implementados.

## Instalação local

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Suba os serviços:

```bash
docker compose up --build
```

Execute as migrations:

```bash
docker compose exec web python manage.py migrate
```

Crie o usuário administrativo:

```bash
docker compose exec web python manage.py createsuperuser
```

## Endpoints

- Administração: `/admin/`
- Documentação Swagger: `/api/docs/`
- Health check: `/api/health/`
- API principal: `/api/v1/`
- Integração IXCSoft: `/api/ixc/`

## Segurança

Nunca publique tokens, senhas, communities SNMP ou chaves de criptografia no
GitHub.

Utilize variáveis de ambiente e secrets protegidos no ambiente de implantação.

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Configuração do IXCSoft](docs/IXC_SETUP.md)
- [Endpoints utilizados no IXCSoft](docs/IXC_ENDPOINTS.md)
- [Histórico de versões](CHANGELOG.md)

## Releases

As alterações de cada versão ficam registradas na página **Releases** do GitHub
e no arquivo `CHANGELOG.md`.

## Licença

A licença definitiva do projeto ainda será definida.
