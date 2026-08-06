# MAP v0.75.54

Hotfix de manutenção: corrige 2 migrations que quebram um `migrate` num
banco Postgres novo. Sem relação com o bug do v0.75.53 — foi encontrado
enquanto eu validava aquele hotfix de verdade, no navegador.

## Contexto

Depois de mergeado o v0.75.53 (PR #124), montei um ambiente de teste
totalmente isolado no servidor de produção (stack Docker própria, banco
Postgres e Redis próprios, rede própria, sem tocar em nada de
`ixcsoft-mapa-*`) pra rodar o Playwright de verdade contra a sequência
exata do bug relatado (abrir Rack → fechar → abrir CTO/CDO/CEO).

Pra isso, precisei subir um banco **do zero** e rodar `migrate` — coisa
que produção nunca fez (o schema dela já existia, incrementalmente,
desde antes dessas migrations serem escritas no formato atual). Isso
expôs 2 migrations reais e quebradas que só aparecem nesse cenário:

1. `apps/access/migrations/0002_add_ftth_fields.py` tentava adicionar 12
   campos (`ixc_customer_id`, `ixc_contract_id`, `onu_mac`, `cto_ixc_id`,
   `ftth_port`, `concentrator_id`, `concentrator`,
   `interface_transmission`, `connection_type`, `last_connection_start`,
   `last_connection_end`, `disconnect_reason`) que `0001_initial.py` **já
   cria** dentro do próprio `CreateModel` de `AccessPoint`. Resultado:
   `django.db.utils.ProgrammingError: column "ixc_customer_id" of
   relation "access_accesspoint" already exists`.
2. `apps/network_map/migrations/0003_sync_company_fields_state.py` usa
   `SeparateDatabaseAndState` com `database_operations=[]` — ou seja, só
   avisa o Django que os campos `company` existem em `FiberCable`,
   `NetworkElement` e `NetworkRoute`, mas nunca manda o `ALTER TABLE`
   de verdade pro banco. Resultado, mais adiante no `migrate`:
   `django.db.utils.ProgrammingError: column
   network_map_networkelement.company_id does not exist`.

## Por que produção nunca bateu nisso

O Django rastreia migration aplicada só pelo **nome** (tabela
`django_migrations`), nunca pelo conteúdo do arquivo. As duas migrations
acima já estão marcadas como aplicadas na produção — os campos foram
criados lá por outro caminho, antes dessas migrations serem reescritas
nesse formato atual. Isso quer dizer:

- Rodar `python manage.py migrate` na produção com este hotfix é
  **no-op** nesses dois pontos — nada é reexecutado, nada muda no banco.
- O problema só existe pra quem precisar subir um banco **novo**: um
  ambiente de teste isolado (como fiz aqui), disaster recovery, ou um
  clone limpo do projeto.

## Correção

- `apps/access/migrations/0002_add_ftth_fields.py`: virou no-op
  (`operations = []`). Não foi apagado — `billing.0001_initial`,
  `ixc_integration.0007_purge_nic_fibra_test_data` e
  `network_map.0007_ctosplitter_ctosplitterport` dependem dele pelo
  nome no grafo de migrations.
- `apps/network_map/migrations/0003_sync_company_fields_state.py`: os
  mesmos 3 `AddField` que já existiam em `state_operations` foram
  espelhados em `database_operations`, pra criar as colunas de verdade
  num banco novo.

## Validação

- `python -m py_compile` nos 2 arquivos de migration tocados.
- `tests/test_map_v07554_contract.py` (novo): confirma que 0002 virou
  no-op preservando a dependência, que 0001 ainda cria os 12 campos
  diretamente, que 0003 tem `database_operations` populado (não mais
  `[]`), que as 3 migrations dependentes continuam apontando pra
  `access.0002_add_ftth_fields` pelo nome, e que nenhuma migration nova
  foi criada — só as 2 existentes foram corrigidas.
- Suíte histórica completa, sem regressão.
- Revisão manual do diff: nenhuma migration nova, `PLATFORM_VERSION`
  inalterada.
- **Não validado num banco novo de verdade nesta rodada** (o ambiente
  isolado onde o bug apareceu já foi derrubado, por instrução do Adrian,
  antes desta correção ser escrita) — a correção foi validada pela mesma
  investigação de código que a encontrou (rastreando exatamente as
  operações de cada migration), não por um `migrate` real repetido. Se
  quiser, dá pra montar o ambiente isolado de novo só pra confirmar ao
  vivo antes de mergear.

## Fora de escopo

- Nenhuma mudança de comportamento visível na aplicação — é só
  infraestrutura de migration.
- Nenhuma migration nova.
- Não investiguei se existem outras migrations com o mesmo problema além
  destas duas — só corrigi as que bloquearam o `migrate` no ambiente
  isolado da v0.75.53.
