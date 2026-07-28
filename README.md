# IXCSoft Mapa

Plataforma para monitoramento e correlação de rede óptica, integrando IXCSoft,
OLTs FiberHome, PostgreSQL/PostGIS, Celery, Redis, Zabbix, Grafana e Telegram.

## Versão 0.5.0

Incluído nesta versão:

- compatibilidade com URL raiz ou `/webservice/v1`;
- listagem IXC via GET conforme WebserviceClient;
- suporte a POST, PUT e DELETE no cliente, sem execução automática;
- sincronização de `cliente`;
- sincronização de `radusuarios`;
- sincronização de `radpop_radio_cliente_fibra`;
- modelo de provisionamento óptico do IXC;
- campos de projeto, CTO, PON, ONU, VLAN e sinal óptico;
- associação inicial Login ↔ CTO ↔ ONU;
- API de consulta para dados de fibra;
- testes do cliente IXC.

## Endpoint novo

```text
/api/ixc/fiber-assignments/
```

## Próximo passo

Subir o ambiente Docker, gerar as migrations e testar a conexão com uma
credencial nova e protegida.
