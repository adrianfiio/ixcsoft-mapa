# Endpoints IXCSoft usados

## Cliente

Tabela: `cliente`

Objetivo: dados cadastrais do assinante.

## Login PPPoE

Tabela: `radusuarios`

Objetivo: login, cliente, situação e associação lógica.

## Provisionamento de fibra

Tabela: `radpop_radio_cliente_fibra`

Campos relevantes:

- `id_login`
- `id_projeto`
- `id_caixa_ftth`
- `porta_ftth`
- `mac`
- `ponid`
- `slotno`
- `ponno`
- `onu_numero`
- `onu_tipo`
- `vlan`
- `vlan_pppoe`
- `sinal_rx`
- `sinal_tx`
- `temperatura`
- `voltagem`
- `data_sinal`
- `causa_ultima_queda`
- `distancia_onu`
- `latitude`
- `longitude`

A aplicação usa apenas operações de leitura durante a sincronização. Operações
de criação, edição e exclusão estão disponíveis no cliente, mas não são
executadas automaticamente.

## Segurança

Nunca coloque token real em:

- GitHub;
- `.env.example`;
- documentação;
- issues;
- screenshots;
- mensagens públicas.

Use o secret `IXC_ENCRYPTION_KEY` e cadastre o token pelo painel administrativo
ou por variável protegida do EasyPanel.
