# Configuração IXCSoft

## Variáveis

```env
IXC_BASE_URL=https://seu-ixc.exemplo.com.br
IXC_API_TOKEN=token-em-basic-auth
```

Também é possível criar a configuração pelo Django Admin ou pela API:

```text
POST /api/ixc/configurations/
POST /api/ixc/configurations/{id}/test-connection/
POST /api/ixc/configurations/{id}/synchronize/
```

O token nunca é retornado pela API.

## Tabelas inicialmente sincronizadas

- `cliente`
- `radusuarios`

Os nomes podem variar conforme versão/customização do IXC. Antes de produção,
valide os endpoints disponíveis no seu ambiente.
