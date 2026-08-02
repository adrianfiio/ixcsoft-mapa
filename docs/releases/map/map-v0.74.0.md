# Mapa v0.74.0

Release exclusiva do componente **Mapa**, baseada no commit
`a141a28ebe2c6de9cf2d264041c9362203bffa54` após a separação oficial de versões.

## Versões após o merge

| Componente | Versão |
|---|---:|
| Plataforma | v0.76.0 |
| Mapa | v0.74.0 |

## Entrega

- Rack/Torre sem reconstrução e chamadas infinitas;
- proteção contra requisições simultâneas;
- snapshot visual SNMP a cada cinco minutos apenas quando aplicável;
- SNMP opt-in por equipamento ativo;
- DIO, PTO, servidor e OLT fora do SNMP universal;
- servidores preservados no banco e ocultados do mapa;
- Rack/Torre, Canvas e ações mais compactos;
- ficha técnica responsiva e imprimível em PDF;
- fusões centralizadas;
- lateral sem barras visíveis e com alternância de nomes;
- menu contextual com ícones.

## Dados e segurança

- nenhuma migration;
- nenhum equipamento, cabo, fibra, fusão ou histórico apagado;
- nenhum segredo incluído;
- perfis antigos incompatíveis são somente auditados até execução explícita do
  comando com `--apply` no servidor.

## Validação obrigatória

```bash
python scripts/validate_map_v074.py
python scripts/check_project.py
python -m compileall -q apps config scripts tests
python manage.py check
python manage.py cleanup_invalid_snmp_profiles
git diff --check
pytest -q tests/test_map_v074_static.py
```

No navegador, abrir Rack/Torre com DevTools → Network e aguardar 60 segundos:
deve existir uma chamada `equipment/` e uma `container-layout-v3/`, sem repetição
causada pela renderização.
