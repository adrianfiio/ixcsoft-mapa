# AFService Map

Plataforma para monitoramento, correlação e visualização geográfica de redes
FTTH, integrada ao IXCSoft e preparada para equipamentos GPON.

O projeto reúne informações cadastrais, acessos PPPoE, provisionamentos FTTH,
infraestrutura óptica, estado de ONUs, sinais e eventos em uma única aplicação.

## Versão atual

**v0.32.1 — Fusão em duas colunas: portas do DIO × cabos do rack**

Esta versão transforma o mapa em um editor de projetos com postes, CTOs, CEOs,
cabos, camadas operacionais e importação KML/KMZ.

## Funcionalidades implementadas

### Integração IXCSoft

- Configurações independentes por empresa
- Armazenamento criptografado do token da API
- Teste de conexão
- Sincronização manual e periódica com Celery
- Clientes da tabela `cliente`
- Logins PPPoE da tabela `radusuarios`
- Provisionamentos da tabela `radpop_radio_cliente_fibra`
- Associação inicial entre cliente, login, CTO e ONU
- Registro das execuções e do resultado das sincronizações

### Infraestrutura GPON

- Cadastro de OLTs
- Portas PON
- ONUs
- Estado operacional e LOS
- RX, TX, temperatura, tensão e distância
- Histórico de sinais ópticos
- Estrutura inicial para coletores SNMP

### Infraestrutura óptica e GIS

- Empresas
- POPs e racks
- Equipamentos de rack
- Rotas ópticas
- Elementos de rede
- OLTs, DIOs, caixas de emenda, CTOs, postes e armários
- Modelos de cabo
- Cabos, tubos e fibras
- Padrões e sequências de cores
- Bandejas e fusões
- Dependências entre elementos
- Geometrias PostGIS
- Base do mapa com Leaflet e OpenStreetMap
- Agrupamento de marcadores
- Busca e filtros por estado
- API GeoJSON para os acessos

### Plataforma

- Django e Django REST Framework
- Administração Django
- API REST
- OpenAPI e Swagger
- PostgreSQL/PostGIS
- Redis
- Celery Worker e Celery Beat
- Docker e Gunicorn
- Health checks de liveness e readiness
- Configuração para proxy HTTPS e EasyPanel

## Estado atual da interface

O dashboard operacional está disponível na página inicial e apresenta
indicadores reais de acessos, clientes, infraestrutura, OLTs, ONUs e alertas.
O mapa permanece integrado à API GeoJSON em uma página própria, disponível em
`/mapa/`.

No editor do mapa, toda nova estrutura pertence a um projeto de rede. Usuários
autenticados podem criar projetos, posicionar postes, CTOs e CEOs, desenhar
cabos, mover elementos e importar KML/KMZ. A visualização de clientes e
estrutura pode ser ligada ou desligada por camada.

A navegação principal reúne os acessos ao dashboard, mapa, equipamentos, OLTs,
ONUs, clientes e alertas. O próximo ciclo do frontend será integrar as telas de
cadastro ao novo layout compartilhado.

## Funcionalidades pendentes

- Coleta SNMP real em OLTs FiberHome
- Perfis de OIDs por modelo e firmware
- Descoberta automática de portas PON e ONUs
- Correlação operacional completa entre IXCSoft e OLT
- Motor de alertas
- Notificações por Telegram
- Integração com Zabbix
- Dashboards no Grafana
- Importação de KML e KMZ
- Integração das telas de cadastro ao layout do dashboard
- Ampliação dos testes automatizados

## Arquitetura

```text
IXCSoft API ───────────────┐
                           ├──> Django API ──> PostgreSQL/PostGIS
OLTs via SNMP (planejado) ─┘         │
                                     ├──> Redis/Celery
                                     ├──> API REST/GeoJSON
                                     ├──> Administração Django
                                     └──> Frontend Leaflet
```

### Domínios

```text
apps/
├── core/
├── access/
├── ixc_integration/
├── olt_integration/
├── optical/
├── network_map/
└── alerts/
```

Cada integração possui camadas próprias para API, clientes externos, serviços,
repositórios e tarefas assíncronas.

## Tecnologias

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- PostGIS
- Redis
- Celery
- Docker
- Gunicorn
- Leaflet
- OpenStreetMap
- drf-spectacular

## Instalação

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha as variáveis obrigatórias:

- `DJANGO_SECRET_KEY`
- `POSTGRES_HOST`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `REDIS_URL`
- `FIELD_ENCRYPTION_KEY`

Opcionais, para o SMTP padrão da plataforma (uso interno/administrativo — não
é usado como reserva para as empresas, que configuram o próprio SMTP em
"Minha administração"):

- `EMAIL_HOST`
- `EMAIL_PORT` (padrão `587`)
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS` (padrão `true`)
- `DEFAULT_FROM_EMAIL`

Suba os serviços:

```bash
docker compose up --build -d
```

Execute as migrations, se não estiverem habilitadas automaticamente:

```bash
docker compose exec web python manage.py migrate
```

Crie um usuário administrativo:

```bash
docker compose exec web python manage.py createsuperuser
```

Se configurou o SMTP padrão da plataforma, teste com o comando nativo do
Django:

```bash
docker compose exec web python manage.py sendtestemail seu-email@exemplo.com
```

## EasyPanel

No EasyPanel, configure o domínio para o serviço `web` na porta interna `8000`.
PostgreSQL/PostGIS e Redis devem ser fornecidos como serviços externos e
informados pelas variáveis de ambiente.

Quando o acesso público utilizar HTTPS, configure:

```env
WEB_URL=https://mapa.exemplo.com.br
DJANGO_SECURE_SSL_REDIRECT=false
```

O proxy reverso deve encaminhar `X-Forwarded-Proto: https`.

## Atualização automática no Debian

No servidor instalado em `/opt/ixcsoft-mapa`, registre o comando global uma
única vez:

```bash
chmod +x scripts/install_apply_command.sh
./scripts/install_apply_command.sh
```

Depois, qualquer atualização pode ser aplicada com:

```bash
apply
```

O comando atualiza a branch `main`, reconstrói os containers, aguarda o health
check e exibe um relatório final. Se houver alterações locais ou algum serviço
falhar, o processo para sem sobrescrever arquivos e mostra os logs recentes.

### Evitar usuário e senha em toda atualização

Por padrão o Git pede usuário e senha do GitHub a cada `apply`, porque o
repositório usa HTTPS. Para não digitar toda vez, no servidor Debian, rode
uma única vez como o mesmo usuário que executa o `apply`:

```bash
git config --global credential.helper store
```

Na próxima chamada de `git fetch`/`git pull` (ou `apply`), quando pedir a
senha, use um **Personal Access Token** do GitHub (Settings → Developer
settings → Personal access tokens → Tokens (classic), com permissão `repo`)
no lugar da senha da conta. O Git guarda a credencial em texto simples em
`~/.git-credentials`; garanta que apenas o usuário que roda o `apply` tem
acesso de leitura a esse arquivo.

Alternativa mais segura, sem token em texto plano: trocar o remoto para SSH
com uma chave de deploy dedicada ao repositório.

```bash
git remote set-url origin git@github.com:adrianfiio/ixcsoft-mapa.git
```

Isso exige gerar uma chave SSH no servidor (`ssh-keygen`) e cadastrá-la em
GitHub → Settings → SSH and GPG keys (ou como Deploy Key do repositório).

## Endpoints principais

- Dashboard: `/`
- Mapa operacional: `/mapa/`
- Administração: `/admin/`
- Equipamentos: `/rede/equipamentos/`
- Swagger: `/api/docs/`
- Schema OpenAPI: `/api/schema/`
- Health check: `/api/health/`
- Liveness: `/api/health/live/`
- Readiness: `/api/health/ready/`
- API principal: `/api/v1/`
- Integração IXCSoft: `/api/ixc/`
- API do mapa: `/api/map/`

## Segurança

Nunca publique tokens, senhas, communities SNMP ou chaves de criptografia.
Utilize variáveis de ambiente e secrets protegidos no ambiente de implantação.

O `.env.example` contém apenas valores ilustrativos.

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Configuração do IXCSoft](docs/IXC_SETUP.md)
- [Endpoints do IXCSoft](docs/IXC_ENDPOINTS.md)
- [Histórico de versões](CHANGELOG.md)

## Licença

A licença definitiva do projeto ainda será definida.
