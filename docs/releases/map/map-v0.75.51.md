# MAP v0.75.51

## Switches tipados, YAML idempotente e cores por velocidade

Esta versão acrescenta uma camada específica para Switches no Canvas do Rack sem substituir o controlador estável da MAP v0.75.50.

### Switch de 16 portas

- A criação de Switches passa a oferecer 16 portas como capacidade explícita.
- Switches de 16 portas são organizados numa única linha horizontal com 16 colunas fluidas.
- O equipamento respeita a largura interna do Rack e não invade as calhas laterais.

### Edição individual das portas

Cada porta pode receber nome, tipo físico e velocidade próprios:

- RJ45;
- SFP;
- SFP+;
- XFP;
- QSFP+;
- 1, 10, 25, 40 ou 100 Gbps.

O editor também permite aplicar conector e velocidade a um intervalo de portas antes dos ajustes individuais. Ligações persistidas não são apagadas durante a edição.

### Importação YAML/YML

O importador seguro aceita o formato NetBox já suportado e o formato `equipment`/`equipments` da MAP v0.75.51. Os nomes das interfaces são preservados exatamente como aparecem no arquivo, inclusive após expansão de intervalos.

A importação utiliza uma chave externa estável quando disponível. Reimportar o mesmo arquivo atualiza equipamento e portas em vez de duplicá-los. `replace_ports` é opcional e nunca remove uma porta ligada.

### Cores de conexão

Porta conectada e linha da ligação compartilham a velocidade efetiva:

- 1 Gbps: verde;
- 10 Gbps: azul;
- 25 Gbps: roxo;
- 40 Gbps: laranja;
- 100 Gbps: vermelho.

Quando os dois lados informam velocidade, a menor é usada. Quando apenas um lado informa, esse valor é usado. Porta livre permanece neutra.

### Compatibilidade e estabilidade

- Sem migration.
- O enum legado `ContainerEquipmentPort.PortType` continua sendo preenchido para manter APIs e ligações existentes.
- Conector, velocidade, origem YAML e chave estável são guardados em `ContainerEquipment.metadata.v07551_port_profiles`.
- O runtime da v0.75.50 continua responsável por Rack, OLT, pan, zoom e proteção contra loops.
- Observers da v0.75.51 apenas reaplicam classes visuais e nunca fazem chamadas à API.
