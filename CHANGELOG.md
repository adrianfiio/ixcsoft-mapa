# Changelog

## [0.72.0] - 2026-08-02

Pacote "Redesign do mapa" preparado pelo ChatGPT sobre o commit `065a3bb`
(v0.71.0 + hotfix v0.71.1 já embutidos no `main` quando apliquei). Aplicado
via `apply_map_ui_v072.py` (validado antes com `--dry-run`). Backup/ponto
de rollback: tag `v0.71.1` (também disponível como branch
`backup/mapa-pre-v072-20260802`). Sem migration.

### Corrigido

- **Causa raiz da sobreposição de abas em Rack/Torre**: o template carregava ao mesmo tempo o editor de estrutura antigo (`container-structure-v09.js`, que monta suas próprias abas Resumo/Equipamentos/Diagrama/Fibras/YAML) e a Master Suite (que monta as abas novas Equipamentos/Canvas 2D/Matriz/Fibras/YAML) — os dois competindo pelo mesmo diálogo. É a mesma raiz por trás do laço de requisições visto ao vivo em produção (print do usuário mostrando `container-layout-v3`/`equipment` repetindo dezenas de vezes por segundo). O script legado foi removido do carregamento; só a Master Suite continua ativa.
- **Whitelabel do mapa**: o mapa mostrava sempre a logo estática da AFService, mesmo quando a empresa já tinha logo/cor configurados em "Minha administração → Marca" (o dashboard já usava isso, o mapa não). Agora usa `current_company.logo`, nome comercial e cor da empresa automaticamente, com fallback pra marca AFService quando não há logo.
- **Alertas exigindo ERP**: o sino de alertas só aparecia pra empresa com integração ERP configurada — mas alerta de porta/enlace SNMP (v0.71.0) não depende de ERP nenhum. Agora aparece pra qualquer empresa provedora (com ou sem ERP), continua oculto pra empresa em modo projetista.
- **Controles soltos "Rastrear"/"Menu"** e o painel antigo de rotas removidos da tela — o novo botão "Rotas" só aparece quando a Master Suite confirma uma rota com ligação real (não só cadastrada pelo nome).

### Adicionado

- **Sidebar operacional nova**: logo da empresa, seletor de projeto, Início, busca, Equipamentos, importar KMZ/KML, Alertas, Configurações, alternar tema, Sair, dados da empresa no rodapé, recolhimento pra 72px, último estado salvo no navegador.
- **Barra de ferramentas única**: Selecionar, CTO, Caixa (CEO/CDO), Poste, Cabo, Régua, Área, Mais (CPD/POP, Rack, Torre), Rotas, Enlaces.
- **Régua que vira cabo**: mede em vários pontos com distância acumulada, e converte o traçado num cabo real (nome, código, tipo, modelo/fibras, origem, destino, descrição) pela API já existente `/api/map/cables/create/`.
- **Ferramenta Área**: mede polígono em m², converte pra hectare/km² automaticamente, exporta em GeoJSON (com `project_id` e `area_m2`).
- **Popups HUD modernos** em CTO/CEO/CDO/Rack/Torre/CPD-POP/Poste/cabo: ícone, nome, tipo, código, status real, ação principal em destaque, ações secundárias organizadas, Excluir em vermelho de verdade, tema escuro/claro. Reaproveita os handlers originais (Cabos e ligações, Equipamentos, Ficha/QR, Fusões, Editar, Excluir, Monitoramento) em vez de recriá-los.
- **Status SNMP no popup só aparece quando existe monitoramento configurado de verdade** (verde/vermelho pulsante, amarelo degradado, cinza sem dados) — não mostra "online" só por o elemento existir.
- **Tema claro/escuro** com botão na sidebar, preferência salva no navegador.

### Nesta rodada

- **Reforço de segurança contra o mesmo tipo de laço do hotfix v0.71.1**: o pacote trazia dois observadores de mutação novos em `map-ui-v072.js`; um já tinha proteção contra reagir à própria mudança, o outro (o que limpa a UI do diálogo de Rack/Torre) não — como ele adiciona classes CSS e o observador escuta mudança de classe, isso podia reagendar a si mesmo sem parar. Adicionei a mesma trava de debounce do observador vizinho antes de liberar.
- Confirmado que o pacote **não toca** em `map-optical-editor-v3.js` nem `map-link-monitoring.js` — os dois arquivos corrigidos no hotfix v0.71.1 continuam intactos.

## [0.71.1] - 2026-08-01

Hotfix urgente a partir de report ao vivo em produção (print do DevTools
mostrando ~8900 requisições em ~60s pra `container-layout-v3`, navegador
travando com `net::ERR_INSUFFICIENT_RESOURCES`). Backup/ponto de
rollback: tag `v0.71.0`.

### Corrigido

- **Laço de requisições ao abrir "Monitoramento" num equipamento dentro de Rack/Torre**: `loadContainerLayout()` (`map-optical-editor-v3.js`) só marcava a requisição como "já carregada" *depois* dela terminar — se algo disparasse a função de novo mais rápido que o tempo de resposta da rede (no caso, decorações de status do monitoramento de portas mexendo no DOM do mesmo diálogo, observadas por outro script), cada chamada concorrente passava pela checagem antes da primeira resposta voltar e abria sua própria requisição. Corrigido com uma trava de "já em andamento" (marcada antes do `await`, não depois) mais um intervalo mínimo de 1s entre buscas — nenhuma requisição concorrente escapa mais, não importa o que estiver disparando a função.
- **Título da porta crescendo sem parar**: cada redecoração de status SNMP (`map-link-monitoring.js`) grudava mais um `· SNMP UP` em cima do título anterior em vez de substituir — inofensivo isoladamente, mas evidência do mesmo problema de raiz (a decoração rodando repetidas vezes sem necessidade). Corrigido pra guardar o título original uma vez e sempre montar a partir dele.
- **Observador de mutações do monitoramento reagindo às próprias mudanças**: ao inserir o botão "Monitoramento" ou decorar portas/equipamentos, o próprio script gerava uma mutação no DOM que disparava seu próprio observador de novo (e o de outros scripts que observam a mesma área). Agora ele se desconecta antes de mexer no DOM e volta a observar só depois, cortando esse laço na origem.

## [0.71.0] - 2026-08-01

Pacote "Monitoramento de portas e enlaces" preparado pelo ChatGPT,
construído em cima do `apps.snmp_monitoring` da v0.68.0. Aplicado via
`apply_monitoring_links_v071.py` (validado antes com `--dry-run`).
Backup/ponto de rollback: tag `v0.70.0` (também disponível como branch
`backup/mapa-pre-monitoramento-v071`). **Tem migrations** (`snmp_monitoring.0002_link_monitoring`
e `alerts.0002_network_monitoring_alerts`) — rodam automaticamente no `apply`.

### Adicionado

- **Monitoramento SNMP nos equipamentos internos de Rack/Torre** (switch, roteador, firewall, servidor, access point, rádio PTP, ONU/ONT, outros) — OLT continua bloqueada aqui de propósito, ela usa a integração própria. Informa IP, porta, community (criptografada, nunca retorna pela API) e intervalo de coleta.
- **Descoberta de portas SNMP** (ifName/ifIndex/ifAlias/status) associável a uma porta física já criada no equipamento, com função (backbone, uplink, acesso, wireless/PTP, gerência, outro) — só as portas vinculadas controlam os enlaces; interface avulsa não derruba o equipamento inteiro.
- **Enlaces de backbone entre cidades**: duas portas monitoradas associadas a um `FiberCable` do mapa, com dois caminhos independentes possíveis (principal/secundário), cada um com portas, cabo, cor e alerta próprios.
- **Enlaces PTP wireless**: linha reta tracejada entre torres, cor configurável (roxo por padrão), sem exigir cabo óptico.
- **Debounce configurável** (padrão 30s para queda e 30s para recuperação) evitando abrir/fechar alerta por oscilação SNMP passageira.
- **Central de alertas ampliada**: novos escopos equipamento/porta/enlace, com `AlertEvent` recebendo `company` diretamente (além de elemento, equipamento, porta, enlace, cabo, rota, projeto) — funciona tanto para empresa com IXCSoft quanto com outro ERP ou só cadastro manual.

### Alterado

- **Consulta ao InfluxDB em lote**: antes era uma consulta por equipamento; agora todos os perfis ativos são consultados juntos, portas/interfaces atualizadas numa única passada, e só depois os enlaces são avaliados. Atualização visual do mapa a cada 15s, coleta Celery a cada 30s (configurável via `SNMP_STATUS_POLL_SECONDS`).
- **Recarga do Telegraf deixou de disparar a cada atualização de telemetria**: o sinal que aciona o `SIGHUP` agora só reage a mudanças de configuração (IP, community, alvo, etc.), não mais a cada ciclo de coleta — no v0.68.0 original, qualquer `save()` do perfil (inclusive os de telemetria, a cada ~30s) disparava reload do Telegraf.

### Corrigido

- **Filtro de empresa nos alertas**: o aplicador do pacote tinha um bug na função que insere `Q(company_id__in=company_ids)` nos dois pontos de filtragem de alerta em `apps/core/views.py` — por um efeito colateral do `.replace()` (o texto substituído continha o próprio marcador de busca), o filtro novo acabou duplicado no primeiro ponto (`_provider_context`, inofensivo — só uma condição OR repetida) e **totalmente ausente no segundo, que é a view real da página "Central de alertas"** (`company_alerts`). Sem esse ajuste, alertas de porta/enlace monitorado (que têm `company` mas não `cto`/`olt`/`route`) não apareceriam na Central de alertas de ninguém. Corrigido manualmente antes de liberar: duplicata removida, filtro certo adicionado em `company_alerts`, e `select_related` da view ampliado para incluir `monitored_link`/`container_equipment`/`equipment_port` (evita consulta N+1 ao listar até 200 alertas).

### Segurança

- Token do InfluxDB continua só por variável de ambiente (o token colado numa conversa anterior segue precisando ser rotacionado no InfluxDB, se ainda não foi).
- Community SNMP criptografada, nunca em texto puro.
- Socket do Docker continua só no `worker` — nenhuma mudança no `web`.
- Recarga do Telegraf continua por `SIGHUP`, sem `os.system`/`docker restart`.

## [0.70.0] - 2026-08-01

Pacote cumulativo "Master Suite" preparado pelo ChatGPT para a área do
mapa, aplicado via `apply_map_master_suite.py` (validado com `--dry-run`
antes). Backup/ponto de rollback: tag `v0.69.0` (também disponível como
branch `backup/mapa-pre-master-suite-20260801`). **Tem migration**
(`network_map.0032_map_master_suite`) — roda automaticamente no `apply`.

### Adicionado

- **Rotas passam a existir de verdade pela topologia dos cabos**, não por proximidade: uma rota só aparece pra seleção quando há uma cadeia conectada de ponta a ponta (POP/Rack/Torre com OLT/DIO → cabo com as duas pontas → CEO/CDO/CTO → demais trechos contínuos). O sistema identifica e reporta cabo desconectado, cabo com uma ponta só, trecho isolado, origem OLT/DIO ausente e caixa sem conexão. Rota agora se atribui direto no cabo (e nos demais elementos), com atalho "Definir rota"/"Sem rota" nos popups.
- **Ícones do mapa configuráveis pelo Django Admin** (`Estilos de ícones do mapa`): SVG, URL de imagem, cores, tamanho e exibição do nome, por empresa — com o comando `seed_map_icon_styles` pra popular os estilos padrão (CTO, CEO, CDO, Rack, Torre, Poste, PTO).
- **Editor de POP/Rack/Torre ganhou 5 abas**: Equipamentos, Canvas 2D, Matriz de manobra, Fibras e terminações, YAML/modelos. No Canvas 2D, equipamentos são arrastáveis (posição persiste), com organização automática, ligações ancoradas nas portas, caminhos ortogonais, pontos de dobra editáveis, cores diferentes por tipo de ligação (fibra/cobre/wireless), tela cheia e exportação em PNG.
- **Inventário técnico ampliado**: roteador, firewall, servidor, ONU/ONT e PTO viram tipos reais de equipamento (antes eram "outro" com metadado); portas RJ45 2.5G, SFP28 25G, QSFP+ 40G, QSFP28 100G, SC/APC, SC/UPC e LC; campos de fabricante, modelo, série, patrimônio, IP, firmware, função, posição/altura em U, face do rack, foto, documentação, uplinks, potência TX e observações; placas de OLT com módulos SFP/SFP+/SFP28/QSFP/DAC/GBIC.
- **CTO e splitters reaproveitam splitters/portas já existentes**, com estados livre/reservada/ocupada/defeituosa, vínculo com cliente/AccessPoint, observações por porta e ficha técnica.
- **Rastreamento óptico**: grafo considerando elementos, cabos, fibras, fusões, splitters, portas internas, equipamentos e ligações (fibra, cobre, wireless) — a tela "Rastrear" mostra o caminho entre origem e destino com nomes de fibras, cabos, equipamentos e portas.
- **Ficha técnica, QR Code e histórico** em elementos, cabos e equipamentos: botão "Ficha/QR", impressão, QR Code em SVG que abre o ativo direto no mapa, estados de implantação (em projeto/não implantado/implantado/certificado/desativado) e histórico com usuário, data e observação.
- **Reserva técnica posicionável e arrastável** sobre a linha do cabo, com metragem, identificação e observações.
- **`qrcode>=8.2,<9`** nas dependências.

### Alterado

- **Menu lateral e controles do mapa menores**, adequados a Full HD/2K, com opção de minimizar ainda mais; painel de rotas antigo saiu da visualização, substituído pela gaveta nova (recolhida por padrão, só aparece quando existe rota válida).
- **Editor de fusões mais compacto e móvel**: cabeçalho e controles menores, maximização por CSS (não abre mais pela metade), botão alterna corretamente para "Desmaximizar" e reposiciona a janela dentro da tela; ações internas (splitter, nota, menu) não derrubam mais a maximização.
- **Ícones menores**, com a repetição visual "CDO CDO" corrigida.

### Corrigido

- **Clique em "Inserir caixa" que criava o elemento mas não continuava o processo**: a API já devolvia `id` na raiz da resposta, mas o código só procurava `result.element.id` — corrigido para aceitar os dois formatos. Também corrigidos: cliques duplicados na inserção (agora bloqueados até a ação terminar), popup fechado antes de inserir, cancelamento com Esc, e a ação não fica mais "presa" pro próximo clique no mapa.
- **Remoção de cabo de uma caixa específica** (sem apagar o cabo do mapa), com proteção contra remover cabo que termina fisicamente ali.
- **Performance**: removido mais um `MutationObserver` que observava o documento inteiro (`map-v092.js`, usado para modernizar o seletor de YAML) — reduz chance de travamento em projetos grandes.

### Nesta rodada

- **Conflito de nomes resolvido**: o pacote criava `apps/network_map/services/` (pasta) ao lado de `apps/network_map/services.py` (arquivo já existente e em uso) — Python não aceita os dois convivendo. Resolvido movendo `map_master_topology.py` para `apps/network_map/map_master_topology.py` (mesmo padrão plano dos outros arquivos `map_master_*.py` do pacote) e ajustando os dois imports que apontavam pro caminho antigo.
- **Migration escrita manualmente**: este ambiente de preparação não tem GDAL nem banco PostGIS, então não dá pra rodar `manage.py makemigrations` aqui. A migration `network_map/migrations/0032_map_master_suite.py` foi escrita à mão a partir da definição exata dos 3 modelos novos (`MapIconStyle`, `MapDiagramRevision`, `NetworkAssetLifecycle`) e das novas choices de `ContainerEquipment`/`ContainerEquipmentPort` — revisar no servidor com `python manage.py showmigrations network_map` e `python manage.py sqlmigrate network_map 0032` antes de confiar cegamente.

## [0.69.0] - 2026-08-01

### Adicionado

- **Tela de carregamento animada logo após o login** (`/carregando/`): mapa de fibra acendendo (OLT → CTO → casa) e rede wireless conectando (torre → torre → casa) em SVG animado, com o fluxo real de login passando por ela antes de cair no dashboard (`LOGIN_REDIRECT_URL`). Logo usa o mesmo PNG já usado no resto do app, em vez de uma URL externa.

### Alterado

- **Fundo da tela de login** ganhou a mesma grade de pontos pulsando e luzes correndo em diagonal da tela de carregamento — a troca entre as duas telas fica contínua, sem "salto" visual.

## [0.68.0] - 2026-08-01

Nova app `apps/snmp_monitoring` — backend do monitoramento de portas por
SNMP (Telegraf/InfluxDB) preparado com a infraestrutura já em produção.
Sem UI ainda (fica pra depois do ChatGPT terminar a rodada atual do
mapa); ver `docs/releases/v0.68.0.md` pra configuração necessária no
servidor antes de ativar.

### Adicionado

- **Modelo `SNMPMonitoringProfile`**: liga um elemento do mapa a um alvo SNMP (IP, porta, community — criptografada com o mesmo mecanismo já usado nos tokens do IXCSoft), com company preenchida automaticamente a partir do elemento.
- **Geração segura do `.conf` do Telegraf**: template versionado (`apps/snmp_monitoring/conf_templates/`), com validação de IP e community antes de gravar o arquivo (evita injeção de configuração), escrita atômica, e recarga do Telegraf por `SIGHUP` (não `restart` — não derruba a coleta de outras empresas).
- **Task periódica `poll_snmp_status`** (Celery Beat, a cada 2 minutos): consulta o InfluxDB por equipamento monitorado e atualiza `NetworkElement.status` (é o campo que já pinta o marcador no mapa) quando alguma porta cai.
- **`influxdb-client` e `docker` (SDK) nas dependências.**

## [0.67.8] - 2026-08-01

### Corrigido

- **`apply` cancelava a atualização de novo**, agora por causa de `consultar_status.py`, mais um script solto do projeto de monitoramento criado direto em `/opt/ixcsoft-mapa`. Adicionado ao `.gitignore`, mesmo tratamento das v0.67.1/v0.67.5.

## [0.67.7] - 2026-08-01

### Alterado

- **Logo da tela de login aumentada** (96px → 168px de largura), ficava pequena demais no painel escuro novo.

## [0.67.6] - 2026-08-01

### Adicionado

- **`influxdb-client` nas dependências** (`requirements.txt`), pro projeto de monitoramento com InfluxDB que está sendo montado no servidor — estava sendo editado direto em produção, o que bloqueava o `apply` (arquivo rastreado, alteração local pendente); agora entra pelo repositório normalmente.

## [0.67.5] - 2026-08-01

### Corrigido

- **`apply` cancelava a atualização de novo**, agora por causa de `equipamentos_ativos_snmp/`, `gerar_equipamento.py` e `templates/equipamentos_snmp/` — pastas/arquivos novos da instalação do InfluxDB, criados direto em `/opt/ixcsoft-mapa` no servidor. Adicionados ao `.gitignore`, mesmo tratamento já dado a `docker-compose-monitor.yml`/`telegraf.conf` na v0.67.1.

## [0.67.4] - 2026-08-01

### Alterado

- **Painel do formulário de login**: fundo trocado de claro para um gradiente escuro (cinza grafite para preto), mais moderno e alinhado ao resto da plataforma. Logo agora centralizada (antes ficava alinhada à esquerda, sem destaque). Textos, campos e a mensagem de erro ajustados pro novo fundo escuro.

## [0.67.3] - 2026-08-01

Backup/ponto de rollback: tag `v0.67.2`. Hotfix da área do mapa preparado
pelo ChatGPT ("v0.10.2" na numeração dele), aplicado via `apply_v0102.py`.
Substitui só `map-optical-editor-v2.js` e `map-optical-editor-v3.js` —
sem banco, migration, dashboard ou configuração de empresa envolvidos.

### Corrigido

- **Performance do Editor Óptico v2/v3 no mapa**: um único `MutationObserver` observava o documento inteiro e reprocessava tudo a cada mudança no DOM, rodando centenas de vezes à toa. Trocado por observadores escopados ao mapa, à tela de fusões e ao diálogo de estrutura, cada um com filtro de relevância e debounce — processa só marcador novo, ignora mudança produzida pelo próprio editor de linhas e não varre o mapa inteiro quando nenhum popup está sendo criado.

## [0.67.2] - 2026-08-01

### Alterado

- **Painel do formulário de login**: fundo branco puro trocado por um leve gradiente (branco para um tom rosado bem suave) — a logo (que já é um PNG transparente) ficava "boiando" sobre um branco muito seco.

## [0.67.1] - 2026-08-01

### Corrigido

- **`apply` cancelava a atualização no servidor** por causa de `docker-compose-monitor.yml` e `telegraf.conf` — arquivos da stack de monitoramento (fora deste repositório, mantidos soltos em `/opt/ixcsoft-mapa`) que apareciam como alteração local não commitada, e o `apply` para de propósito nesse caso pra não sobrescrever nada. Adicionados ao `.gitignore` — o `apply` deixa de enxergá-los como pendência.

## [0.67.0] - 2026-08-01

Backup/ponto de rollback: tag `v0.66.0` (também disponível como branch
`backup/mapa-pre-v0101-20260801`). Pacote cumulativo de correções da área
do mapa preparado pelo ChatGPT ("v0.10.1" na numeração dele), aplicado
via `apply_v0101.py` (validado com `--dry-run` antes).

### Corrigido

- **Alcance automático de cabo em CTO/CEO/CDO reduzido para 45 metros**, e cabo de outra rota deixa de entrar automaticamente numa caixa que já tem rota definida — cabo distante que a API antiga ainda retornasse fica oculto da fusão.
- **Ícones do mapa refeitos**: CTO com formato de caixa retangular, CEO/CDO com formato de fechamento vertical, Rack como gabinete e Torre sem texto solto dentro do marcador — corrigida a repetição visual "CDO CDO". Nome continua no rótulo acima do marcador.
- **Editor de fusões mais compacto**: cabeçalho e barra de controles menores, mais área para fibras e splitters; maximização por CSS não sai mais da tela cheia ao abrir menu, splitter ou nota.
- **Painel de filtro por rota só aparece quando existir cabo ou elemento realmente associado a uma rota** — rota vazia não ocupa mais espaço no painel.
- **Opções de PTO/conector direto só aparecem quando o cabo selecionado é realmente do tipo DROP.**

### Adicionado

- **Botão "Cabos" dentro da tela de fusões**: remove um cabo só daquela caixa (sem apagar do mapa), com opção de restaurar depois — cabo que termina fisicamente na caixa fica protegido contra remoção indevida.
- **"Definir rota" nos popups de cabo, CTO, CDO, CEO e demais elementos**, com opção de trocar a rota ou marcar "Sem rota definida".
- **Botão "Detalhes" nos equipamentos de rack/torre**, abrindo janela com fabricante, modelo, número de série, IP, descrição, observações, foto por URL, portas, placas e módulos instalados por porta (SFP óptico 1G, SFP/RJ45 1G, SFP+ 10G, SFP28 25G, DAC, GBIC, outro).
- **Diagrama interno da estrutura**: botão "Mover" para posicionar equipamentos livremente (posição persiste), botão "Editar linhas" (duplo clique adiciona ponto de dobra, arrastar move, botão direito remove) e botão "Auto" para voltar ao posicionamento automático.
- **Terminação de cabo DROP em porta óptica existente, PTO nova ou conector direto** (SC/APC, SC/UPC, LC/UPC, LC/APC) — PTO/conector viram equipamentos passivos da estrutura, já selecionáveis como destino.

## [0.66.0] - 2026-08-01

### Alterado

- **Tela de login redesenhada**: painel de formulário claro (campos com ícone, foco destacado) ao lado de um painel escuro com a proposta da plataforma e um card de destaque — layout inspirado em telas modernas de login SaaS. Cor de destaque (botão, foco dos campos) trocada de ciano para vermelho, alinhada com a identidade da empresa. Sem alteração de fluxo: continua só usuário/senha, sem cadastro público e sem alternância claro/escuro no resto do sistema.

## [0.65.0] - 2026-08-01

Backup/ponto de rollback: tag `v0.64.0` (também disponível como branch
`backup/mapa-pre-v0100-20260801`). Pacote "Editor Óptico v2" preparado
pelo ChatGPT para a área do mapa ("v0.10.0" na numeração dele), aplicado
via `apply_v0100.py`.

### Adicionado

- **Inserir caixa direto no cabo**: ao clicar num cabo, a opção agora é "Inserir caixa" — abre uma janela compacta pra criar uma CTO/CDO/CEO nova ou conectar uma já existente, escolher entre cortar (dois segmentos) ou registrar passagem sem cortar, definir a capacidade da CTO e arrastar a prévia da caixa sobre o cabo antes de confirmar. Pra ligar dois ou mais cabos na mesma caixa, basta repetir a inserção em cada cabo escolhendo "Conectar caixa existente" e selecionando a mesma CTO/CDO/CEO. O corte continua usando a rotina segura já existente (bloqueia cabo com fusões ou terminações); se a caixa for criada mas o corte falhar, o sistema desfaz a caixa automaticamente, sem deixar ponto abandonado.
- **Passagem sem corte**: novo endpoint autenticado pra registrar que um cabo passa por uma CEO/CDO/CTO sem cortar — o cabo passa a aparecer na caixa e pode ser cortado depois, direto na tela de fusões.
- **Linhas de fusão editáveis**: modo "Editar linhas" — clique pra selecionar, arraste os pontos de dobra, duplo clique adiciona ponto, botão direito num ponto remove, "Ortogonal" reorganiza a ligação, "Automático" remove o desenho manual. O caminho fica salvo (no mesmo layout JSON já existente, sem migration) e continua lá ao fechar e abrir de novo.
- **Cores por tipo de ligação**: fibra óptica em ciano, cobre/RJ45 em laranja, wireless em roxo tracejado (fibras mantêm suas cores reais); linha selecionada ganha destaque visual.

### Corrigido

- **Editor de fusões menor e móvel**: ocupa menos espaço, pode ser arrastado pela barra do título, mantém o mapa visível atrás, cabeçalho mais compacto e mais área útil pro diagrama — continua com tela cheia, desmaximizar e zoom com Ctrl + rolagem.

## [0.64.0] - 2026-08-01

Backup/ponto de rollback: tag `v0.63.0` (também disponível como branch
`backup/mapa-pre-v092-20260801`). Pacote preparado pelo ChatGPT para a
área do mapa ("v0.9.2" na numeração dele), aplicado via `apply_v092.py`.

### Adicionado

- **CPD/POP pela barra lateral, barra recolhida e clique direito**, com edição de CPDs importados anteriormente. Ao criar/editar, é possível escolher o funcionamento físico: somente ponto CPD/POP, Rack/sala técnica ou Torre/site externo — o ponto continua identificado visualmente como CPD/POP mesmo funcionando como Rack ou Torre.
- **OLT dentro da Torre** (cadastro manual e importação YAML), além de switch, DIO, rádio PTP, access point e ONU/ONT já suportados.
- **CDO em todos os pontos de criação do mapa**: barra lateral, barra recolhida, clique direito, criação manual, inserção no meio do cabo e conversão de reserva — com marcador e popup próprios. Internamente continua sendo uma caixa de emenda, preservando o subtipo `cdo`.
- **Painel de filtro por rota**: Todas, Nenhuma, botão "Só" por rota, seleção de várias rotas, mostrar/ocultar reservas e mostrar/ocultar traçados. Ao filtrar por uma rota, mostra só os cabos, CTOs e CEO/CDO relacionados, reservas dos cabos visíveis e o CPD/POP conectado — combinável com os filtros gerais já existentes (CTO, CEO/CDO, cabos, nomes). CTO usa a relação direta com a rota; CEO/CDO e CPD recuperam a rota pelos metadados do KMZ e pelas passagens; rotas sem geometria própria também aparecem no seletor.
- **Equipamentos da torre/rack agrupados por categoria** (OLTs, DIOs, switches, rádios PTP, access points, ONUs/ONTs, outros) em vez de despejar todas as portas na tela — as portas continuam disponíveis no diagrama interno e nas terminações.

### Corrigido

- **Diagrama interno da torre/rack reorganizado** em três áreas (OLT/DIO → switches/equipamentos centrais → ONU/rádio/AP), com linhas saindo e chegando na porta correta, traçado ortogonal, sem atravessar o centro dos cards, e cores diferentes por tipo de ligação (fibra, cobre, wireless).
- **Seletor de importação YAML modernizado**: área de upload com clique ou arrastar-e-soltar, nome/tamanho do arquivo, botão Limpar e botão Procurar arquivo, no lugar do seletor antigo.

## [0.63.0] - 2026-08-01

### Adicionado

- **Sino de alertas no topo da tela**, ao lado do nome do usuário, para empresas provedoras com integração ERP ativa: mostra um indicador quando há alerta ativo, um clique abre uma lista com os últimos alertas e um atalho para a Central de alertas completa.
- **Painel "Infraestrutura por tipo" agora existe pronto pra usar, mas não aparece sozinho**: fica disponível no editor de dashboard (aparece esmaecido com a caixa "Visível" desmarcada) pra quem quiser ligar; quem não mexer não vê nada de novo.

### Corrigido

- **Ícone da "Infraestrutura"** (cartão do dashboard e item "Equipamentos" do menu lateral, que agora usam o mesmo ícone) trocado pelo símbolo antigo de losango por um ícone de servidor/rack.
- **Botão "Abrir mapa"** (Visão geral, dashboard do projetista e Visão da plataforma) ganhou o mesmo ícone de mapa usado na tela de equipamentos, no lugar do caractere de texto que não lembrava nada.
- **Espaçamento em "Minha administração"**: a barra "Adicionar à rede" estava colada no painel "Configurações da empresa" acima dela, parecendo que um elemento subia por cima do outro.

## [0.62.0] - 2026-08-01

### Adicionado

- **Novo painel "Infraestrutura por tipo" no dashboard das empresas provedoras**: torres, racks, ONUs cadastradas, CTOs, CEOs/caixas de emenda e total de equipamentos internos (nas torres e nos racks), cada linha levando direto pra lista de equipamentos filtrada por tipo — reaproveita o mesmo padrão de atalho já usado no dashboard do projetista.

### Corrigido

- **Barra de rolagem feia nos painéis do dashboard editável**: agora usa a mesma barra fina e discreta já usada no mapa/editor (cor de destaque, sem o padrão cinza grosso do navegador).
- **Ícones de "Visão geral" e "Mapa"** (menu lateral e topo da tela de equipamentos) trocados de caractere de texto por SVG — o antigo não lembrava nada (não era nem um mapa nem um globo).
- **"Central de alertas" não aparece mais em "Minha administração" para empresa projetista** — projetista não tem cliente pra monitorar, então a central de alertas não se aplica.
- **Empresa projetista não consegue mais abrir a página de alertas direto pela URL** (antes só o menu escondia o link; agora o acesso é bloqueado também no servidor).

## [0.61.2] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.61.1` (também disponível como branch `backup/mapa-pre-v091-20260801`). Pacote de correções preparado pelo ChatGPT para a área do mapa (v0.9.1) — aplicado via `apply_v091.py`, todos os patches bateram exato.

### Corrigido

- **Erro CSRF ao salvar na estrutura de torre/rack**: o JavaScript colocava `X-CSRFToken` nos headers, mas a mesclagem de `options` sobrescrevia o objeto inteiro quando a requisição também definia `Content-Type`, apagando o token e causando 403 "CSRF token missing". Corrigida a ordem de mesclagem; token também fica disponível via campo oculto no HTML como alternativa ao cookie.
- **HTTP 500 ao abrir CTOs importadas antigas**: CTO sem splitter/bandeja cadastrado ainda podia existir com `splitter_ratio` vazio, e a API quebrava tentando montar a estrutura com esse valor vazio. Agora essas CTOs são reparadas automaticamente (splitters recriados por capacidade) ao serem abertas.
- **Terminação óptica direto em SFP/SFP+**: cabo alimentador/distribuição/backbone só pode terminar em DIO; só cabo DROP pode ir direto pra SFP/SFP+, e agora exige escolher PTO+cordão ou conector direto no transceiver. Porta PON de ONU não aparece mais como destino nesse formulário (ela é destino de DROP, não de terminação genérica). Perda óptica aceita vírgula ou ponto decimal.
- **Alinhamento do assistente KMZ e da tela de fusões**: campos de Rotas e Ligações ficam com proporções/larguras iguais, botão Detectar/Recalcular ligações ganhou linha própria; fusões mais compactas, tela cheia ocupando a janela inteira (com botão "Desmaximizar"), zoom com Ctrl+scroll.
- **Estrutura de torre/rack usa a largura toda** da janela (antes sobrava espaço vazio à direita); linhas do diagrama passam por trás dos cards, não por cima das portas.

### Adicionado

- **CTO importada cria splitter automaticamente pela capacidade** (8→1:8, 16→1:16, 24→1:16+1:8, 36→1:32+1:4, 48→1:32+1:16, 128→dois 1:64), com portas comerciais e visuais já prontas para o diagrama de fusões.

## [0.61.1] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.61.0`.

### Corrigido

- **Logo do whitelabel ficava alinhada à esquerda** dentro da caixa reservada no menu lateral (e no preview da página "Marca da empresa") sempre que a proporção da imagem enviada não batia exatamente com o espaço — agora fica centralizada.
- **Logo da tela de login** (a padrão da AFService — essa tela não tem como saber a empresa antes do login) ficava colada no topo do painel esquerdo, com um vão grande até o texto. Agora fica centralizada verticalmente no painel.

### Adicionado

- **Recomendação de tamanho no upload da logo** (página "Marca da empresa"): texto de ajuda sugerindo proporção retangular (ex.: 300×100px) e fundo transparente, já que a logo sempre aparece numa caixa de 150×50 no menu.

## [0.61.0] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.60.2` (também disponível como branch `backup/mapa-pre-v09-20260801`). Pacote preparado e aplicado pelo ChatGPT (área do mapa/KMZ) via `apply_v09.py` — todos os patches bateram exato, sem incompatibilidade pra resolver.

### Adicionado

- **CEO/CDO tem prioridade sobre CTO em cabo tronco.** Cabos de distribuição, alimentador e backbone agora preferem uma CEO/CDO próxima (alcance próprio, 45m por padrão, configurável na etapa Ligações) em vez de uma CTO — DROP continua preferindo CTO normalmente. Uma decisão individual no assistente sempre pode sobrescrever a sugestão automática.
- **CEO/CDO passa a mostrar todos os cabos próximos**, não só os que já têm origem/destino nela — inclui cabos registrados como passagem e cabos de lotes antigos a até 45m, resolvendo o caso em que um cabo só "passava perto" e nunca aparecia no diagrama de fusões. CTO continua restrita às relações explícitas (pra não competir pelo cabo tronco da caixa de emenda vizinha).
- **Cortar cabo de passagem direto nas fusões**: um cabo que só passa pela CEO/CDO aparece com aviso e botão "Cortar na caixa" — o corte divide o cabo em dois segmentos no ponto real da caixa, atualiza origem/destino, gera as fibras do novo trecho, move reservas e entra no mesmo lote KMZ (Desfazer lote continua removendo tudo). Fibras de um cabo de passagem ficam bloqueadas até o corte; o corte é bloqueado se o cabo já tiver fusões ou terminações.
- **ONU/ONT com portas LAN configuráveis** (1, 2, 4 ou 8 Gigabit) — cria automaticamente PON 1 (SC/APC) + as portas LAN numeradas.
- **Diagrama interno de torre/rack**: liga porta por porta (óptica↔óptica vira fibra, RJ45↔RJ45 vira cobre, wireless↔wireless vira enlace), com zoom, organizar, ajustar e tela cheia.
- **Fusões ganham botão de tela cheia**, mantendo zoom/organizar/ajustar/automático já existentes.
- **Assistente KMZ**: painel de prioridade CEO/CDO na etapa Ligações (alcance próprio + raio de prioridade configuráveis), indicação do papel do cabo (tronco ou DROP) nas ligações detectadas, e a tela final após importar com sucesso mostra só "Importação concluída" + botão Fechar (sem mais Voltar/Continuar/Importar novamente, que não faziam sentido ali).

## [0.60.2] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.60.1`.

### Corrigido

- **Upload de logo (whitelabel) não funcionava em produção**: o upload salvava normalmente, mas a imagem nunca carregava (ícone quebrado). Causa: a rota de mídia usava `django.conf.urls.static.static()`, um helper do Django que só gera a rota quando `DEBUG=True` — em produção (`DEBUG=false`) ela virava um no-op silencioso, então `/media/...` nunca batia em lugar nenhum. Trocado por `django.views.static.serve` direto, sem essa checagem.
- **Editor de dashboard (Gridstack) com scrollbar feia nos cards**: mesmo com o tamanho/posição já corrigidos na v0.60.1, o CSS que vem junto do Gridstack.js define `overflow-y: auto` por padrão nos itens, aparecendo como uma barra de rolagem mesmo sem nada pra rolar. Cartões agora não rolam nunca; painéis continuam podendo rolar se ficarem pequenos demais depois de redimensionados.

### Adicionado

- **Botão de escolher arquivo mais moderno** na página de whitelabel (Marca da empresa) — troca o botão cinza padrão do navegador por um no estilo do resto do sistema; a caixa de "arquivo atual"/"limpar" do Django (redundante com o preview que já existia acima) foi removida.
- **Ícones no topo da tela de Equipamentos** ("Visão geral"/"Mapa"), mesmos ícones já usados no menu lateral.
- **Cards de CTO/CEO/DIO/OLT no dashboard do projetista** agora usam os mesmos ícones do mapa (em vez de um losango genérico) e viram atalho: clicar num card fora do modo de edição abre a tela de Equipamentos já filtrada por aquele tipo.

## [0.60.1] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.60.0`.

### Corrigido

- **Editor de dashboard (v0.59.0) renderizava quebrado**: cards estreitos, sobrepostos, com scrollbar. Causa: `.widget-grid` era `display: grid` o tempo todo, inclusive durante a edição — mas o Gridstack.js posiciona os itens com `position: absolute` própria, e ter os dois motores de layout (CSS Grid do navegador e o cálculo do Gridstack) atuando ao mesmo tempo sobre os mesmos elementos quebrava o tamanho/posição de cada card. Agora o `display: grid` só vale fora do modo de edição; durante a edição o Gridstack assume o layout inteiro, sem concorrência.
- **Tela de Equipamentos** (`/rede/equipamentos/`) tinha um cabeçalho isolado, sem a marca/cor da empresa (usava uma paleta vermelha fixa própria, sem checar `current_company`) e com um bug de link: o botão "Mapa" apontava para a Visão geral em vez do mapa. Agora essa tela também reflete o whitelabel (logo e cor de destaque) da empresa, o botão "Equipamentos" (redundante, já que é a própria página) foi removido, e o nav passa a ser "Visão geral" + "Mapa" (o Mapa agora vai pro lugar certo).

### Alterado

- **"Alertas" sai do menu lateral para empresas do tipo projetista** (sem clientes, então sem alertas de acesso pra acompanhar) — continua visível normalmente para provedores. Volta quando o motor de alertas cobrir monitoramento de equipamentos, que hoje ainda não existe.

## [0.60.0] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.59.0` (também disponível como branch `backup/mapa-pre-v08-20260801`). Pacote preparado e aplicado pelo ChatGPT (área do mapa/KMZ/estruturas internas) — aplicado via script (`apply_v08.py`, patches exatos com backup automático de cada arquivo tocado), sem reimplementação.

### Corrigido

- **Erro "O modelo do cabo não possui padrão de cores" ainda podia bloquear a importação.** A causa real: um gerador de fibras antigo (`apps/optical/services/fiber_generator.py`), disparado por um signal ao criar o `FiberCable`, interrompia a criação ANTES do importador chegar ao próprio fallback de cores (já corrigido na v0.56.0). Esse gerador antigo agora é um adaptador fino do serviço seguro (`apps.network_map.services.generate_cable_fibers`) — mesmo fallback de sempre (padrão do modelo → paleta `FiberColor` → paleta técnica automática). O importador também passa a checar se o signal já gerou a estrutura antes de tentar gerar de novo, evitando duplicidade.

### Adicionado

- **Torre e rack aceitam mais tipos de equipamento**: torre agora aceita Switch, Access point, Rádio PTP, DIO e ONU/ONT/Outro; rack aceita OLT, DIO, Switch e ONU/ONT/Outro. Sem migration — ONU é um `ContainerEquipment` do tipo `other` com `metadata.equipment_subtype = "onu"`, exibido como "ONU / ONT" na interface.
- **Importação de Device Type YAML** (subconjunto do formato usado pela biblioteca de tipos de dispositivo do NetBox): tela da torre/rack ganha "Importar YAML de equipamento" — escolhe o arquivo, pré-visualiza fabricante/modelo/interfaces, escolhe o tipo no mapa e importa, criando as portas automaticamente (RJ45 100M/1G, SFP, SFP+, wireless, PON). Exemplo incluído: `examples/device-types/mikrotik-rb911g-5hpacd.yaml`.
- **Terminação óptica ampliada**: uma fibra já podia ser fundida numa porta de DIO; agora também termina em porta PON (de ONU), SFP e SFP+ — continua não permitindo terminar direto numa porta RJ45 (elétrica), corretamente.
- Abertura do painel "Gerenciar estrutura" (torre/rack) não recarrega mais a estrutura inteira do mapa ao abrir — mesma lógica já aplicada às Fusões na v0.56.0, evitando concorrência com o popup do Leaflet.

## [0.59.0] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.58.1`.

### Adicionado

- **Dashboard redimensionável (arrastar a borda, tipo Zabbix/Grafana).** O editor de widgets (dashboard de empresa, do projetista e "Visão da plataforma") deixa de só reordenar dentro de zonas fixas — agora é um grid livre de 12 colunas: arrasta pra qualquer posição e redimensiona pelo canto, como um dashboard builder de verdade. Reaproveita a mesma infraestrutura de esconder/mostrar e mensagem no topo já existente.
  - **Só no modo de edição** carrega uma biblioteca nova (Gridstack.js, via CDN — mesmo padrão do SortableJS que ela substitui). A visualização normal do dashboard **não carrega nenhuma dependência nova**: o servidor já sabe a posição/tamanho de cada widget e renderiza com CSS Grid puro, sem JavaScript de layout.
  - Modelo de dados trocado: `widget_order`/`hidden_widgets` (duas listas) viram um campo só, `widget_layout` (posição x/y, tamanho w/h e visibilidade por widget). Layouts já customizados antes desta versão são convertidos automaticamente (migration com conversão de dados), preservando ordem relativa e o que estava escondido.
  - Widget sem posição salva ainda (board novo, ou widget que apareceu depois da última edição) cai em auto-flow — mesmo espírito da ordem padrão de antes, só que em duas dimensões.

## [0.58.1] - 2026-08-01

Backup/ponto de rollback desta rodada: tag `v0.58.0`.

### Corrigido

- **Whitelabel: cor de destaque não alcançava tudo.** Só o `--primary` era trocado pela cor escolhida pela empresa; realces derivados (fundo do item ativo do menu, cor do texto ativo, banner no topo do dashboard) continuavam com o teal padrão, hardcoded separadamente. Agora `--primary-soft`, a cor do texto ativo do menu e o gradiente/borda do banner são calculados a partir de `--primary` (via `color-mix()`), então acompanham automaticamente qualquer cor de whitelabel escolhida.

## [0.58.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.57.0` (também disponível como branch `backup/mapa-pre-v07-20260731`).

Handoff v0.7 do ChatGPT (`IMPORTAR KMZ CHATGPT/IXCSoft_MAPA_v0.7_Handoff.md`) — desta vez só especificação, sem código pronto, então esta rodada foi implementada aqui a partir da descrição, comparando com o que já existia (vários itens já tinham sido resolvidos nas v0.56.0/v0.57.0 e não precisaram de trabalho novo: fallback de cor de fibra, histórico em badges, primeiro clique em Fusões, zoom/organizar/ajustar, reparo de fibras).

### Corrigido

- **Prévia do KMZ podia ficar "grudada" no mapa**: fechar o assistente pelo X, ou trocar o projeto selecionado enquanto uma prévia estava desenhada, não limpava a camada temporária (`state.previewLayer`, `kmz-import-wizard.js`) — agora os dois casos chamam a limpeza, além dos pontos que já existiam (importar com sucesso, reiniciar análise).

### Adicionado

- **Importador KMZ mais largo e com menos espaço vazio**: modal até `min(96vw, 1680px)` (era 1480px), gutters laterais reduzidos.
- **Scrollbar fina e discreta** no conteúdo do assistente, tabelas e listas de exceções — antes era a barra padrão do navegador.
- **Etapa Cabos**: cards com grid de 4 colunas (Ação | Tipo | Fibras/Metragem | Modelo), mesma altura entre cards de ações diferentes, nomes/pastas longos com clamp de 1-2 linhas (tooltip com o texto completo).
- **Etapa Rotas**: botões "Marcar todas", "Desmarcar todas" e "Marcar somente rotas com linhas"; checkbox trocado por um toggle moderno arredondado.
- **Etapa Ligações**: seção "Aplicar para todos" com 2 selects (CTO no meio / CEO-CDO no meio) + botão — aplica a regra a todas as ligações já detectadas de uma vez, sem precisar editar uma por uma (os selects de padrão já existentes continuam só valendo para novas detecções).
- **Sidebar do mapa mais compacta**: menos espaçamento vertical entre seções, scrollbar fina.
- **Trilha lateral recolhida completa**: antes só aparecia com a sidebar em modo de edição (e mesmo assim, sem botão de voltar); agora sempre mostra botão "← Voltar para visão geral" e um ícone de olho (camada "Geral") — as ferramentas de desenho continuam só em modo de edição.
- **Ícone de olho nas camadas**: os checkboxes de camada (CTO, CEO, cabos, clientes...) na sidebar agora mostram ⊙ (visível) ou ⊘ (oculto) em vez do checkbox nativo — mesmo comportamento por baixo, só a aparência mudou.

## [0.57.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.56.0`.

### Adicionado

- **Menu lateral retrátil**: o botão ☰ (antes só funcional no mobile) agora também recolhe/expande a barra lateral no desktop, liberando espaço de tela — funciona para qualquer usuário (empresas e superusuário), estado salvo no navegador (`localStorage`), persiste entre páginas.
- **"Visão da plataforma" em tela cheia para o superusuário**: como essa página já é o "dashboard" do superadmin desde o redirect da v0.55.0, e ele já tem o Django admin para o resto, a barra lateral some nessa tela — fica só o conteúdo, o botão "Editar este painel" e um novo botão "Abrir mapa" (que substitui o link que sumiu da barra lateral).

### Corrigido

- **Dashboard do projetista** (`dashboard_designer.html`) tinha só uma coluna, forçando "Dados da empresa" e "Atalhos" um embaixo do outro sem opção de ficarem lado a lado — diferente do dashboard de provedor, que já tinha 2 colunas. Agora tem as mesmas 2 colunas.
- Editor de dashboard: o arrastar-e-soltar (SortableJS) passa a usar o modo "fallback" (emulado por mouse/touch) em vez do drag nativo do navegador — o drag nativo podia deixar o "ghost" (espaço reservado semitransparente do item sendo arrastado) preso na tela em vez de sumir ao soltar.

### Sobre o pacote do mapa/KMZ

A partir de agora, entregas do ChatGPT para a área do mapa (`apps/network_map/`, `map-editor.js`, KMZ) são só recebidas, viram backup e são publicadas — sem reescrever a lógica dele aqui. Só a v0.56.0 teve uma revisão profunda (e havia motivo: 3 problemas reais encontrados). Essa área agora é responsabilidade dele, que já acompanha o repositório no GitHub; Claude foca no dashboard/whitelabel e no restante do projeto.

## [0.56.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.55.0` (também disponível como branch `backup/mapa-pre-v06-20260731`).

### Corrigido

- **Cabos importados por KMZ ficavam sem fibras**: o importador só procurava um `CableModel` já cadastrado; sem um compatível, o cabo era salvo sem tubos/fibras (inclusive DROP de 1 FO). Agora a importação cria/reaproveita um modelo técnico gerável para qualquer quantidade de fibras e chama `generate_cable_fibers()` explicitamente. Lotes já importados (como o lote #1) podem ser corrigidos sem reimportar: histórico → **Gerar/reparar fibras** — ação idempotente, não recria fibra em cabo que já tem.
- **Primeiro clique em "Fusões" não abria** (piscava e exigia um segundo clique): o clique recarregava toda a estrutura do mapa ao mesmo tempo em que o popup do Leaflet fechava e o modal tentava abrir. O modal agora abre imediatamente com um indicador de carregamento, sem recarregar a estrutura inteira.
- Tela de fusões: zoom inicial em 70% (era 50%), "Ajustar" agora considera largura E altura disponíveis, "Organizar" usa a altura real dos cartões para não sobrepor colunas, e as setas nativas de campos numéricos foram trocadas por controles `− valor +` consistentes com o resto do sistema.
- Histórico de importação mostrava o resumo do lote como JSON cru (`{"ctos":261,...}`) — agora aparece como indicadores legíveis (261 CTOs, 313 cabos, 24 rotas etc.).

### Sobre a integração deste pacote

Este pacote veio pronto (ZIP + patches) de uma sessão de trabalho externa focada só no mapa/KMZ, em paralelo ao trabalho de dashboard/whitelabel desta mesma rodada (v0.55.0) — áreas de arquivo totalmente separadas, sem conflito. Antes de aplicar, a revisão encontrou e corrigiu 3 problemas no pacote original que não foram copiados como vieram:

- `kmz_import_models.py` revertia `KMZImportObject.batch` para `related_name="objects"` — isso sobrescreve o manager padrão `KMZImportBatch.objects` (o Django troca o atributo de classe pelo descriptor da relação reversa), quebrando `KMZImportBatch.objects.create/filter(...)` em qualquer lugar do sistema. Esse related_name já tinha sido corrigido para `tracked_objects` na migration `0031`, por causa exatamente desse bug; o pacote revertia a correção sem saber da nossa migration. Restaurado, e os dois pontos do novo `kmz_import_api.py` que assumiam o related_name errado (reparo de fibras e "Desfazer lote") foram ajustados para `batch.tracked_objects`.
- A limpeza de importações antigas (`cleanup_legacy_kmz_import`, que exige digitar "LIMPAR {código do projeto}" antes de apagar) perdeu o filtro `cable__project=project` nas reservas candidatas — sem ele, a limpeza de um projeto podia apagar `CableReserve` de OUTRO projeto (de qualquer empresa) só por ter uma nota contendo "Importado do KMZ". Filtro restaurado.
- `CHANGELOG.md` e `README.md` do projeto real tinham sido sobrescritos pelo changelog/readme do próprio pacote (histórico de versões "v0.6/v0.5/v0.4" do pacote, não deste projeto) — restaurados a partir do commit anterior antes desta entrada ser escrita.

## [0.55.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.54.0`.

### Adicionado

- **`/` redireciona para "Visão da plataforma" quando o usuário é superusuário** — a "Visão geral" antiga não mostrava nada de útil pra quem administra a plataforma inteira (números agregados sem separar por empresa, alertas de clientes que o superadmin não acompanha). Empresas continuam vendo a própria "Visão geral" normalmente; nada muda pra elas.
- **Cliente edita o próprio dashboard**: qualquer usuário com permissão EDIT na própria empresa agora vê um botão "Editar dashboard →" direto na "Visão geral", sem depender do superusuário. Mesmo arrastar-e-soltar, esconder cartões/painéis e mensagem no topo da v0.52.0/v0.53.1 — só mudou quem pode ligar o modo de edição (antes só o superusuário via `/painel/dashboards/<empresa>/`, agora também a própria empresa, sempre restrito à empresa do usuário logado, nunca a de outra). O fluxo do superadmin (`/painel/dashboards/`, "Editor de dashboards →") continua existindo, útil pra editar em nome de uma empresa como suporte.
- **Whitelabel: logo e cor por empresa** — nova página "Marca (whitelabel)" em "Minha administração" (usuários EDIT): upload de logo (até 2MB) e escolha de uma cor de destaque. Aplicado automaticamente na barra lateral (logo) e no tema (`--primary`) pra todos os usuários daquela empresa; sem configurar, continua a marca padrão da AFService. Primeiro upload de arquivo do projeto — adiciona `Pillow` como dependência e passa a servir `/media/` (antes não existia rota nenhuma pra isso, mesmo com o volume `media_data` já montado no `docker-compose.yml`).

## [0.54.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.53.1`.

### Adicionado

- **"Visão da plataforma"** — novo item na barra lateral, só pra superusuário: um dashboard detalhado com o resumo de cada empresa ativa (clientes, km de cabo, elementos de rede, alertas ativos, tamanho da equipe e status da sincronização com o ERP), totais somados da plataforma inteira, e um painel "Precisa de atenção" (onboarding incompleto, nunca sincronizou, sincronização atrasada ou com falha). Editável do mesmo jeito que o dashboard de empresa (`?edit=1`): arrastar pra reordenar, esconder cartões/painéis, mensagem no topo — reaproveitando a mesma infraestrutura da v0.52.0/v0.53.1 (`CompanyDashboardLayout`, `dashboard-layout-editor.js`, `widget_edit_bar.html`), agora generalizada para um layout único da plataforma (`PlatformDashboardLayout`, sem empresa dona).
- Não muda o que a "Visão geral" (`/`) mostra hoje pra superusuário — a visão da plataforma fica em URL própria (`/painel/plataforma/`).

## [0.53.1] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.53.0`.

### Corrigido

- **Arrastar não funcionava no editor de dashboard**: cada widget tinha `order: N` fixado por CSS (pra funcionar sem JS na visão normal da empresa) — mas o SortableJS reordena movendo nós de verdade no DOM, e o `order` fixo fazia o item voltar pra posição antiga visualmente assim que soltava, mesmo com o arrastar "funcionando" por baixo. Corrigido: a ordem agora fica numa custom property (`--order`) e só vira `order` de CSS de verdade fora do modo de edição (`.dashboard-edit-mode`); dentro do editor, o JS reordena o DOM de verdade a partir de `--order` antes de inicializar o arrastar.
- Se o SortableJS não carregar (falha de rede/CDN), o editor agora avisa e continua deixando mostrar/esconder e salvar funcionando — antes, a falta da biblioteca travava a tela inteira silenciosamente.
- Painel "Sincronização IXCSoft" da visão geral renomeado para "Sincronização com ERP", com o nome do provedor (ex.: IXCSoft) mostrado dinamicamente abaixo — o sistema não é exclusivo de um único ERP, só o IXC está integrado hoje por já termos acesso a ele.

## [0.53.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.52.0`.

### Corrigido

- Assistente KMZ, etapa "Pontos": ao mudar um grupo pra CTO, o campo mostrava "16" mas o valor não era gravado no estado — cada uma das 143 CTOs de um grupo era cobrada individualmente na validação, mesmo com o valor "certo" visível na tela. Corrigido tanto no frontend quanto no backend (`kmz_topology.py`): regra do grupo e exceção individual agora fazem *merge* (a exceção só sobrescreve os campos que ela de fato define, herdando o resto do grupo — antes ela substituía o objeto inteiro), e valores padrão (CTO → 16 portas, RT → 20 m, DIO → 24 portas, CEO/CDO → subtipo CEO) são aplicados automaticamente quando o campo fica vazio.
- "Gerar e abrir prévia no mapa" não fazia nada visível quando havia pendências — agora informa quantas pendências existem e abre automaticamente a primeira etapa (Cabos ou Pontos) que precisa de ajuste.
- Mapa não recalculava o tamanho depois de fechar o modal da prévia (ficava com área cortada até a próxima interação) — adicionado `map.invalidateSize()` antes e depois de desenhar a camada temporária.

### Adicionado

- Seletor de arquivo moderno no assistente KMZ: arrastar-e-soltar, ícone, nome/tamanho do arquivo, botão "Selecionar"/"Trocar arquivo" — substitui o input nativo do navegador.
- Etapas "Cabos" e "Pontos" do assistente agora usam cartões responsivos (CSS Grid `auto-fit`/`minmax`, container queries, `clamp()`, `dvh`) em vez da tabela larga anterior, que ficava apertada em zooms/resoluções diferentes.

Obs.: o pacote recebido também trazia cópias desatualizadas de `kmz_import_api.py` e `kmz_import_models.py` (sem as correções de `related_name` e do vazamento entre projetos da v0.50.2/v0.50.3) — não foram aplicadas; só os 3 arquivos documentados (`kmz-import-wizard.js`, `kmz-import-wizard.css`, `kmz_topology.py`) entraram nesta versão.

## [0.52.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.51.0`.

### Adicionado

- **Editor visual de dashboard por empresa, admin-only**: em "Minha administração" (superusuário), novo link "Editor de dashboards →" abre uma lista de empresas; escolher uma abre o dashboard dela em modo de edição, com arrastar-e-soltar (SortableJS, via CDN) pra reordenar cartões/painéis, checkbox pra esconder/mostrar cada um, e um campo de mensagem opcional exibida no topo do dashboard daquela empresa. Só o superusuário edita — a empresa nunca vê nem controla essa tela, só o resultado salvo.
  - Novo modelo `CompanyDashboardLayout` (`apps/core/models.py`): ordem/visibilidade dos widgets e a mensagem, por empresa.
  - Novo registro `apps/core/dashboard_widgets.py`: chaves e rótulos dos widgets de cada variante do dashboard (provedor/projetista).
  - `DashboardView` foi refatorada (`_provider_context`/`_designer_context` viraram métodos reaproveitáveis) pra que o editor renderize o dashboard de qualquer empresa escolhida, não só a do usuário logado.
  - Sem layout salvo pra uma empresa, o dashboard continua exatamente como sempre foi — ordem e visibilidade padrão do template, nada muda pra quem nunca foi customizado.

## [0.51.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.50.3`.

### Adicionado

- A visão geral (dashboard) de empresas provedoras (com clientes) ganhou dois cartões de destaque que só existiam na visão de projetista: **Clientes** (total de clientes sincronizados do IXC, com total de ONUs vinculadas) e **Cabos** (km de cabo desenhado no mapa, com total de OLTs cadastradas). Antes, `cable_km` nem era calculado para empresas provedoras — só entrava no contexto do template de projetista.

## [0.50.3] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.50.2`.

### Corrigido

- Excluir projeto travava com `ProtectedError` ao apagar cabos que têm fusão registrada: `FiberSplice.input_fiber`/`output_fiber` usam `on_delete=PROTECT` sobre `FiberStrand`, então apagar o cabo (que cascadeia até a fibra) falhava enquanto a fusão ainda existisse apontando para ela. `wipe_project_structure` agora apaga as fusões do projeto antes dos cabos.
- Pelo mesmo motivo, `olt_integration.OLT.cpd` protege o POP — apagar o POP de um projeto com OLT cadastrada nele quebraria do mesmo jeito. Agora essas OLTs são apagadas antes do POP. A tela de confirmação também passou a mostrar as contagens de fusões e de OLTs do CPD/POP.

## [0.50.2] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.50.1`.

### Corrigido

- **Causa real do 500 ao excluir projeto**: `KMZImportObject.batch` usava `related_name="objects"`, que sobrescreve o manager padrão `KMZImportBatch.objects` (o Django troca esse atributo de classe pelo descriptor da relação reversa). Qualquer `KMZImportBatch.objects.filter/create/get(...)` quebrava com `AttributeError: 'ReverseManyToOneDescriptor' object has no attribute 'filter'`. Isso não afetava só a tela nova — as telas de histórico/desfazer importação KMZ (`v0.48.0`) e a própria gravação do lote na importação definitiva também estavam quebradas desde então, só que ninguém tinha chegado nesse ponto ainda. Renomeado para `related_name="tracked_objects"`, com migration.
- **Número de versão errado em Alertas e Minha administração**: `app_version` só era injetado manualmente no contexto de duas views (Dashboard e Mapa); as demais páginas caíam no valor padrão fixo do template (`0.7.0`). Agora `app_version` vem de um context processor global, disponível em toda página automaticamente.

## [0.50.1] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.50.0`.

### Corrigido

- Erro 500 sem nenhum rastro nos logs: com `DEBUG=false` (produção), o Django só registrava erro 500 por e-mail (`mail_admins`) — sem `ADMINS` configurado, o traceback simplesmente desaparecia, sem aparecer em `docker compose logs`. Adicionado um `LOGGING` explícito que sempre imprime o traceback completo do erro no console, independente de `DEBUG`. Isso não corrige nenhum bug funcional específico — é o que faltava pra conseguir enxergar o erro 500 ao excluir um projeto (em investigação).

## [0.50.0] - 2026-07-31

Backup/ponto de rollback desta rodada: tag `v0.49.0`.

### Adicionado

- **Excluir projeto pelo painel "Minha administração"**: cada projeto listado em `/painel/` agora tem um link "Excluir projeto" (visível só para quem tem edição em alguma empresa). Ele leva para uma tela de confirmação que mostra quantos elementos, cabos, rotas, lotes de importação KMZ e POP serão perdidos, e só executa a exclusão se o usuário digitar o código exato do projeto — igual ao padrão já usado no comando `wipe_network_project`. A exclusão apaga toda a estrutura e o projeto em si (diferente do comando de manutenção, que zera a estrutura mas mantém o projeto).
- `apps/network_map/services.py` ganhou `project_structure_counts()` e `wipe_project_structure()`, reaproveitadas tanto pela tela nova quanto pelo comando `wipe_network_project` (antes a lógica de apagar estava duplicada só no comando).
- `base.html` (o layout usado por praticamente todas as páginas "de site", fora do editor de mapa) não tinha nenhum bloco pra mostrar mensagens do Django (`messages.success`/`messages.error`) — elas eram geradas mas nunca apareciam na tela. Corrigido; agora aparecem no topo do conteúdo, coloridas por tipo (sucesso, erro, aviso, info).

## [0.49.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.48.1`.

### Corrigido

- Botões "Editar"/"×" dos splitters no diagrama de fusões da CEO/CTO estavam sem nenhum estilo (botão padrão do navegador). Agora seguem o tema escuro do editor, com destaque vermelho no excluir.
- "Informações de rota" no diagrama de fusões abria um `alert()` nativo do navegador com o texto cru. Agora abre um painel próprio, com o trajeto desenhado em cadeia (OLT → D.I.O → CEO/CDO → splitter...), a perda acumulada e a potência estimada, com botões para **Imprimir** (usa a caixa de impressão do navegador, dá pra salvar como PDF) e **Exportar (Excel/CSV)**.

## [0.48.1] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.48.0`.

### Adicionado

- Comando de manutenção `wipe_network_project`: apaga toda a estrutura de rede de um projeto (postes, CTOs, cabos, tubos/fibras, splitters, fusões, reservas, lotes de importação KMZ), preservando o projeto em si. Segue o mesmo padrão de segurança do `reset_company_imported_data` já existente: roda em modo simulação por padrão (mostra as contagens sem apagar nada) e só apaga de verdade com `--confirm <código-do-projeto>`.

## [0.48.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.47.0`.

### Corrigido

- Limpeza do importador legado (`cleanup-legacy`): a busca de reservas técnicas por texto na anotação (`notes__icontains="Importado do KMZ"`) não estava restrita ao projeto atual — em tese podia listar/apagar reservas de cabos de outro projeto se o texto coincidisse. Agora a busca fica sempre restrita aos cabos do projeto em questão.
- Índice do modelo `KMZImportBatch` sem nome explícito, o que exigiria rodar `makemigrations` no servidor para descobrir o nome gerado pelo Django antes de aplicar; agora o índice já tem nome fixo e a migration foi escrita à mão, testada campo a campo contra os modelos reais.

### Adicionado

- **Assistente de importação KML/KMZ — nova versão com topologia física**: agora com sete etapas (arquivo, cabos, pontos, rotas, ligações, prévia, importar).
  - Linhas pretas com nome "Drop 01 FO" são reconhecidas automaticamente como cabo Drop de 1 fibra, separadas do restante das linhas pretas/sem estilo (que continuam em "Revisar").
  - Uma linha ou cor "CABO RESERVA" fica separada como reserva desenhada, não misturada com cabo comum.
  - A coluna de dados extras agora muda conforme o tipo do ponto: CTO pede portas, RT pede metragem, DIO pede capacidade de portas, CEO/CDO pede subtipo (CEO/CDO/genérica) — nunca mais aparece "portas" para um ponto que não é CTO.
  - **Bloqueio real de pendências**: enquanto existir qualquer linha ou ponto em "Revisar", ou um cabo sem fibra/tipo, ou uma CTO sem portas, etc., a importação fica bloqueada tanto na tela quanto no backend (HTTP 409 com a lista exata do que falta).
  - **Prévia obrigatória antes de gravar**: existe uma prévia "bruta" (arquivo cru, sem decisão nenhuma aplicada) disponível desde a etapa de classificação, e uma prévia "topológica final" que já mostra os cabos segmentados, códigos propostos, origem/destino e cortes — ambas desenham no mapa sem gravar nada. A prévia final gera um token (hash do arquivo + decisões); qualquer alteração invalida o token e exige gerar de novo.
  - **Cabos passando por caixas**: o importador detecta quando um cabo passa perto de uma CTO/CEO/CDO e sugere Conectar na ponta, Cortar (vira dois `FiberCable` com origem/destino preenchidos), Passar sem cortar (fica registrado como passagem física, sem dividir o cabo) ou Criar derivação — cada relação pode ser revisada individualmente antes de confirmar.
  - **Nomenclatura padronizada**: cabos e equipamentos importados recebem código no padrão `CAB-PREFIXO-ROTA-NNN`, `DROP-...`, `CTO-...`, `CEO-...`/`CDO-...`; o nome original do KMZ, a pasta e o arquivo ficam preservados nos metadados do lote (o nome visível do equipamento pode continuar sendo o original, por escolha).
  - **Lote de importação com desfazer**: cada importação vira um lote (arquivo, usuário, data, resumo); a tela mostra o histórico de lotes do projeto com botão "Desfazer", que remove só os objetos daquele lote (cabos, rotas, CTOs, elementos, reservas, passagens) sem tocar no que já existia antes.
  - **Limpar teste antigo**: para quem já testou a importação de versões anteriores (sem lote), uma ação separada localiza só os objetos com o padrão de código/metadata dos importadores antigos (`KMZ-*`, `IMP-*`, `KML-*`) e exige digitar `LIMPAR <CÓDIGO DO PROJETO>` para confirmar.
  - Nova tela "Cabos e ligações" no popup de qualquer elemento do mapa (CTO, CEO/CDO, poste, etc.), mostrando cabo de entrada, cabo de saída e as passagens/cortes/derivações registradas.

## [0.47.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.46.0`.

### Corrigido

- Orçamento óptico: quando um splitter alimenta outro splitter em cascata (ex.: 1:8 → 1:2) sem uma fibra própria cadastrada entre os dois, a entrada (ENT) do splitter filho não trazia nenhuma informação de rota. A porta do splitter de origem agora é percorrida diretamente, sem depender de uma fibra intermediária.
- Assistente de importação KML/KMZ: a prévia no mapa usava `window.map`, que não existe (o Leaflet fica em uma variável local do editor); o mapa agora é exposto via `window.networkMap` e a prévia usa a referência correta.
- Cabos importados do KMZ agora tentam casar automaticamente com um modelo de cabo já cadastrado (mesma empresa, mesma quantidade de fibras); quando existe, tubos e fibras são gerados sozinhos. Quando não existe, o cabo é criado do mesmo jeito (igual ao desenho manual de cabo) e um aviso indica que as fibras precisam ser geradas depois.

### Adicionado

- **Assistente de importação KML/KMZ — fase 2 (revisão completa e gravação real)**: o assistente ganhou seis etapas — arquivo/análise, cabos por cor, classificação de pontos, escolha de rotas, prévia e importação definitiva. Linhas pretas ou sem estilo entram como "Revisar" por padrão (não são mais assumidas como cabo). Pastas só entram como candidatas a rota quando o nome contém a palavra "ROTA" — a raiz do projeto, `CABOS`, `POP`, `CTO`, `CEO` e `CDO` não aparecem mais nessa lista. Um botão "Desenhar prévia no mapa" carrega temporariamente pontos e linhas no Leaflet (sem gravar) para clicar e conferir o que cada traço representa antes de decidir. Ao confirmar, a importação roda dentro de uma transação atômica: pastas de rota viram `NetworkRoute`, linhas viram `FiberCable`, CTOs viram `CTO`, CEO/CDO/postes/racks/OLT/DIO viram `NetworkElement`, e RT/reserva é associada ao cabo importado mais próximo (respeitando distância máxima) e vira `CableReserve`. POP é importado como `NetworkElement` do tipo Outro (o modelo de POP atual é único por projeto).
- O importador antigo (`import_project_file`, que gravava direto e transformava toda linha em rota) foi removido do projeto — substituído integralmente pelo assistente novo.

## [0.46.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.45.0`.

### Corrigido

- Fusões da CEO/CTO: a entrada (ENT) de um splitter — tanto quando alimentada por uma fibra quanto em cascata de outro splitter — não tinha informações de rota calculadas. Corrigido; agora toda ligação mostra o caminho e a potência estimada.

### Adicionado

- **Assistente de importação KML/KMZ — fase 1 (análise, sem gravar)**: nova tela "Importar KML/KMZ" analisa o arquivo e mostra, antes de qualquer gravação: cores de cabo encontradas (com opção de definir a quantidade de fibras por cor), pastas candidatas a rota, e grupos de pontos sugeridos automaticamente (CTO/NAP → CTO; CEO/CDO/CE/emenda → caixa de emenda; RT/reserva/sobra → reserva técnica; nomes numéricos → CTO com confiança baixa, exigindo confirmação). Essa etapa não grava nada no banco — só organiza a decisão. A importação de verdade (gravação) é o próximo passo.

## [0.45.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.44.0`.

### Adicionado

- **Orçamento óptico completo por ligação, na CEO/CTO**: passar o mouse numa linha de fusão ou saída de splitter mostra o caminho todo (OLT → DIO → cabo → CEO → splitter → ...) com a perda acumulada e a potência estimada chegando ali, calculando inclusive a atenuação da fibra por KM (0,35 dB/km, padrão de mercado). Clicar na linha agora abre duas opções — "Informações de rota" e "Excluir" — em vez de excluir direto.

## [0.44.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.43.0`.

### Corrigido

- **Sinal de luz exigia salvar algo sem relação para atualizar**: criar/remover um cordão, fusão ou splitter não atualizava o mapa por trás do diálogo — só percebia a mudança depois de editar e salvar outra coisa qualquer. Agora o mapa atualiza sozinho toda vez que esses diálogos abrem ou uma ligação muda.

### Adicionado

- **Potência de saída da OLT (manual)**: campo novo no cadastro da OLT para informar a potência óptica de saída (dBm) quando não há coleta SNMP.
- **Perda óptica por ligação**: cordão e fusão agora guardam uma perda estimada (dB), com valor padrão sensato (0,5 dB cordão / 0,1 dB fusão) que pode ser conferido antes de desligar uma ligação.
- **Perda dos splitters**: o diagrama de Fusões da CEO agora mostra a perda estimada ao lado da proporção do splitter — balanceados usam a tabela padrão da indústria (1:2 a 1:64), desbalanceados calculam a perda de cada perna a partir do percentual.
- **Antes de excluir, mostra o cálculo**: clicar num cordão ou fusão já ligada agora mostra a perda e a potência estimada chegando no cabo antes de perguntar se quer desligar.

## [0.43.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.42.0`.

### Alterado

- Diagrama de Fusões do rack: agora dá para criar a fusão começando por qualquer lado — clique na porta do DIO primeiro e depois na fibra do cabo, ou clique na fibra primeiro e depois na porta, como já era. Antes só funcionava fibra → porta.

## [0.42.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.41.0`.

### Adicionado

- **Sinal de luz agora avisa o que aconteceu**: ao escolher uma OLT na lista "OLT de origem", o mapa mostra um aviso dizendo quantos cabos foram iluminados — ou, se nenhum cabo for encontrado, avisa para conferir se existe cordão da PON e fusão de fibra na mesma porta do DIO. Isso torna visível se o problema é a OLT não ser encontrada ou o desenho não aparecer.

### Corrigido

- Diagrama da estrutura (Equipamentos do rack/torre): removido o espaço grande e vazio à direita do painel — a coluna de formulários (Adicionar placa/portas) só ocupa espaço quando um desses formulários está realmente aberto.
- Barra de rolagem do diálogo de Equipamentos redesenhada para combinar com o tema escuro.

## [0.41.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.40.0`.

### Corrigido

- Cadastro de cabo: o nome não vem mais pré-preenchido com "12F" antes de você escolher o modelo — só aparece a quantidade de fibras depois que você escolhe o modelo. "Modelo / quantidade de fibras" agora é obrigatório, e o campo "Quantidade de fibras" só existe para mostrar o que o modelo escolhido define (não dá mais para digitar um número solto ali).

### Adicionado

- Diagrama da estrutura (Equipamentos do rack/torre) ganhou controle de zoom, mais espaçamento entre os botões Editar/Excluir e ajustes para telas pequenas (celular).
- Lista "OLT de origem" do sinal de luz agora identifica no próprio nome se a OLT é um elemento avulso no mapa ou uma OLT dentro de um rack, pra facilitar escolher a certa.

### Investigado

- Sinal de luz da OLT ainda não aparecendo: revisei toda a lógica adicionada na v0.40.0 (resolução do caminho OLT → DIO → cabo) linha por linha e não encontrei erro no código. Preciso de uma confirmação sua pra continuar: depois do apply, a OLT que você ligou aparece na lista "OLT de origem" (com o texto "· rack NOME")? Se não aparecer, o problema é na busca do cabo no servidor. Se aparecer mas a luz não acender, o problema é no desenho do mapa — são causas bem diferentes e preciso saber qual pra corrigir certo.

## [0.40.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.39.0`.

### Corrigido

- **Causa raiz da linha desalinhada ao dar zoom/rolar no diagrama de Fusões**: as linhas eram calculadas usando a posição na tela (que muda com zoom e rolagem) num SVG que não acompanhava esses dois efeitos ao mesmo tempo. Reescrito para calcular a posição das linhas do mesmo jeito que os blocos são posicionados — agora o SVG vive dentro do mesmo bloco que é ampliado/reduzido, então linha e bloco sempre andam juntos, em qualquer zoom, rolagem ou depois de arrastar.
- O menu de botão direito (Adicionar splitter/nota) também não considerava a rolagem da tela ao calcular onde colocar o novo bloco — corrigido junto.

### Adicionado

- **Sinal de luz da OLT reconhece o caminho novo (OLT → DIO → cabo)**: antes, o seletor de "OLT de origem" só enxergava OLTs cadastradas como elemento avulso no mapa (o jeito antigo). Agora também lista as OLTs cadastradas dentro de um rack, resolvendo o caminho cordão (OLT → porta do DIO) + fusão (porta do DIO → fibra do cabo) para descobrir qual cabo de fato sai daquela OLT.

## [0.39.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.38.0`.

### Corrigido

- **Direção do recolher estava invertida**: ao recolher um cabo/DIO no diagrama de Fusões, a intenção é esconder o que **já está ligado** e continuar mostrando só o que falta ligar. A v0.38.0 tinha feito o oposto (escondia o livre, mostrava o em uso). Corrigido nos dois diagramas (CEO e rack); recolhido agora mostra só as portas/fibras livres.
- **Linha "arco-íris"**: o desvio automático de linha adicionado na v0.38.0 (para não passar por dentro de blocos) criava um arco grande e feio em vez de desviar de forma discreta. Como piorou o visual em vez de melhorar, foi revertido — linhas voltam a ser as curvas/retas/ortogonais diretas de antes. Desviar de obstáculo de verdade fica para uma solução futura mais bem pensada.

### Adicionado

- **Bloqueio de sobreposição**: ao arrastar um cabo ou splitter no diagrama de Fusões, ele não entra mais por cima de outro bloco — o movimento para na borda em vez de sobrepor. Notas continuam livres para se sobrepor a qualquer coisa.

## [0.38.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.37.0`.

### Corrigido

- **Nota não salvava a posição ao arrastar**: a posição arrastada era gravada numa chave do layout que o desenho nunca lia de volta — a nota sempre voltava para o lugar original ao reabrir. Corrigido nos dois diagramas de Fusões (CEO e rack).
- **Recolher um bloco escondia as portas em uso, e não as livres**: o recolher era só um recorte visual (mostrava o topo da lista, o que calhasse estar lá). Agora, ao recolher, só as portas/fibras **livres** somem — as que estão em uso continuam visíveis, e a linha continua desenhando para elas normalmente.
- Linhas do diagrama de Fusões da CEO agora desviam por cima quando o caminho reto passaria por dentro de outro bloco no meio do caminho (splitters em cascata, por exemplo). Ainda não é um roteador perfeito, mas resolve o caso comum de uma linha atravessando uma caixa.

### Alterado

- Removido o botão "Fechar" grandão do rodapé do diálogo de Fusões — o × no canto já fecha, e sobra mais espaço pro diagrama.
- Barra de rolagem do diagrama e das listas de portas/fibras redesenhada para combinar com o tema escuro.

## [0.37.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.36.0`.

### Corrigido

- **Causa da linha "falhada" no diagrama de Fusões do rack**: rolar a tela dentro do diagrama não redesenhava as linhas, então elas ficavam apontando para a posição antiga (antes de rolar), parecendo quebradas. Corrigido: rolar a tela agora redesenha as linhas, na CEO e no rack.
- Diagramas de Fusões (CEO e rack) agora permitem recolher qualquer bloco manualmente, mesmo com portas/fibras em uso — quando recolhido, mostra um resumo "X/Y em uso" no título e simplesmente não desenha linha para dentro dele (em vez de apontar para um lugar errado).

### Adicionado

- **Editar equipamento**: OLT e DIO cadastrados no rack (e switch/AP/PTP na torre) agora têm um botão "Editar" para alterar nome, fabricante, modelo, número de série, IP de gerência, cadastro SNMP e tipo de conector — antes só dava para excluir e recadastrar.
- **Cordão colorido por tipo de conector**: porta do DIO ligada à OLT fica azul quando o DIO é UPC e verde quando é APC.
- **Ligação de cordão por clique**: no rack, ligar uma PON da OLT a uma porta do DIO agora é clicar na porta PON e depois na porta do DIO, direto nos cards de equipamento — sem formulário de seleção no meio. A torre continua usando o formulário (switch/AP/PTP/wireless têm mais combinações possíveis).
- Diagrama de Fusões do rack: botão direito no fundo do quadro agora também adiciona nota (igual à CEO).

### Alterado

- Equipamentos do rack/torre (OLT, DIO, switch, AP, PTP) agora aparecem empilhados um embaixo do outro em vez de lado a lado.

### Pendente

- As linhas do diagrama de Fusões ainda são curvas retas ponto-a-ponto — não desviam de blocos no caminho. Fazer isso direito (roteamento que evita obstáculos) é um projeto de desenho maior, ainda não feito.
- Splitter dentro do diagrama de Fusões do rack ainda não existe — hoje um splitter só liga fibra a fibra (CEO/CTO), e as portas do DIO no rack não são fibras. Preciso entender melhor o que a saída de um splitter ligaria ali antes de implementar.

## [0.36.0] - 2026-07-30

Backup/ponto de rollback desta rodada: tag `v0.35.0`.

### Corrigido

- **DIO voltou a não pedir IP nem Cadastro Manual/SNMP** — reversão da v0.35.0, que tinha passado a exibir esses campos. DIO só tem Nome, Fabricante, Quantidade de portas e Tipo de conector.
- **Linhas que sumiam no diagrama de Fusões da CEO**: uma fibra fundida que ficava dentro de um cabo recolhido (não expandido) tinha sua posição real fora da área visível do card, e a linha era desenhada até esse ponto invisível, parecendo "perdida" no canto do diagrama. Agora todo cabo com pelo menos uma fibra em uso expande automaticamente e não pode mais ser recolhido manualmente, garantindo que a linha sempre aponte para um ponto visível.
- Mesmo problema corrigido no diagrama de Fusões do rack: DIO/cabo com porta ou fibra em uso expande automaticamente.

### Alterado

- **Bandejas saíram da tela de edição da CEO** ("Editar CDO" não pede mais quantidade de bandejas, splitters por bandeja nem proporção). Esse formulário salvava esses 3 campos a cada edição — mesmo só mudando o nome — e resetava a proporção de **todos** os splitters da CEO para o mesmo valor toda vez. Agora a CEO cria uma bandeja interna (invisível para o usuário) e splitters são adicionados livremente dentro do próprio diagrama de Fusões.
- **Diagrama de Fusões da CEO**: splitters agora são blocos independentes, arrastáveis e sem a caixa "Bandeja X" ao redor. Botão direito no fundo do diagrama abre um menu para **Adicionar splitter** (com lista de proporções balanceadas 1:2 a 1:64 e desbalanceadas 10/90, 15/85, 20/80, 30/70, 40/60, 45/55) ou **Adicionar nota** (bloco de texto livre, arrastável, editável e removível, para anotações no diagrama).
- Diagrama de Fusões (CEO e rack) agora abre com zoom ajustado automaticamente à tela na primeira vez, em vez de sempre abrir em 100%.

## [0.35.0] - 2026-07-30

### Corrigido

- **Causa raiz encontrada**: campos que deveriam ficar ocultos nos formulários dentro dos diálogos do mapa (ex.: Cadastro Manual/SNMP e Modelo/Número de série do DIO) continuavam aparecendo mesmo com a lógica de ocultar correta. O CSS `.editor-dialog label { display: block; }` sobrescrevia o atributo `hidden` do HTML em qualquer `<label>` dentro desses diálogos. Faltava a regra `.editor-dialog label[hidden] { display: none; }`. Isso também explica o problema relatado antes com o formulário da OLT manual.
- Diagrama de Fusões da CEO: adicionado um redesenho extra 150ms após abrir e redesenho ao redimensionar a janela, para os casos em que as linhas não terminavam de aparecer na primeira renderização do diálogo.

### Adicionado

- Splitters da CEO/CTO agora podem ser ligados em cascata: a saída de um splitter pode alimentar a entrada de outro splitter (inclusive em outra bandeja), sem precisar de uma fibra de cabo entre eles. Selecione a saída do splitter de origem e clique no "ENT" do splitter de destino.
- Diagrama de Fusões do rack (DIO ↔ cabo) ganhou o mesmo editor livre da CEO: blocos arrastáveis, zoom e posições salvas — em vez do layout fixo em duas colunas.

### Pendente

- O diagrama de Fusões da CTO ainda usa a lista simples antiga (sem desenho de linhas nem arrastar). Trazer a CTO para o mesmo editor gráfico da CEO é um trabalho maior, ainda não feito.

## [0.34.0] - 2026-07-30

### Corrigido

- No diagrama de "Fusões" do rack, uma porta do DIO já ligada ao cordão da OLT aparecia como "ligada" mesmo sem nenhuma fibra fundida nela. Causa: o modelo só permitia uma ligação por porta de DIO, então o cordão (frente da porta) e a fusão (fundo da porta) competiam pelo mesmo registro. Agora uma porta de DIO pode ter as duas ligações ao mesmo tempo — cordão para a OLT e fusão da fibra do cabo — e o diagrama de Fusões só mostra "ligada" quando existe mesmo uma fibra fundida.
- No diagrama de Fusões do rack, DIOs e cabos trocam de lado: DIOs sempre à esquerda (entrada), cabos sempre à direita (saída), igual à convenção já usada na CTO/CEO.

### Alterado

- A seção "Fusões — OLT → DIO" dentro de "Estrutura" foi renomeada para "Ligações de cordões — OLT → DIO", já que ali só se registra o cordão (patch cord) da frente da porta, não uma fusão. Ganhou um botão "Abrir Fusões" que leva direto ao diagrama de fusões do rack.
- Cadastro de DIO volta a pedir IP de gerência (opcional) e ganhou o campo "Tipo de conector" (SC/APC, SC/UPC, LC/LC UPC, LC/LC APC).

## [0.33.0] - 2026-07-30

### Adicionado

- Botão "Fusões" no popup do rack no mapa, igual ao que já existe para CTO/CEO. Abre um diagrama visual dedicado: cabos ligados ao rack (com suas fibras coloridas) de um lado, DIOs cadastrados do outro. Clique numa fibra e depois numa porta do DIO para criar a fusão; clique numa fibra ou porta já ligada para desfazer. Uma linha conecta visualmente cada fibra à porta correspondente.
- A fusão agora é registrada no nível da fibra específica (não só do cabo inteiro), reaproveitando o mesmo modelo de fibras coloridas já usado na CTO/CEO.

### Removido

- A lista de fusão rápida (portas do DIO à esquerda, cabos à direita) dentro do modal "Estrutura" do rack, substituída pelo diagrama dedicado acima. O formulário de ligação PON da OLT ↔ porta do DIO dentro de "Estrutura" continua exatamente como estava.

## [0.32.1] - 2026-07-30

### Adicionado

- Fusão rápida por clique, dentro da seção "Fusões" do rack: portas livres do DIO listadas à esquerda, cabos ligados ao rack à direita — clique numa porta e num cabo para criar a fusão direto, sem preencher formulário. Fica lado a lado com o formulário por seleção que já existia (mantido como estava).

## [0.32.0] - 2026-07-30

### Adicionado

- Fusão direta de cabo numa porta do DIO: na seção "Fusões" do rack, agora dá para ligar um cabo que chega no rack diretamente a uma porta do DIO, sem precisar de uma porta de OLT do outro lado. A porta de origem fica opcional — deixe em branco para esse tipo de fusão.
- O diagrama de portas do rack mostra o nome do cabo vinculado direto no card da porta, em vez de só "· ligada".

### Alterado

- Empresas projetistas (sem ERP, sem clientes) deixam de ver as camadas "Clientes online"/"Clientes offline" e o agrupamento de PPPoE no mapa, já que nunca têm esse tipo de dado.
- Cadastro de DIO no rack pede só Nome, Fabricante e Quantidade de portas.
- Cadastro de OLT no rack: modo Manual pede só Nome e Fabricante; modo SNMP soma IP de gerência e Community. Modelo e Número de série saíram do formulário de OLT e DIO (continuam disponíveis para switch/AP/PTP na torre).
- Diagrama de fusões da CTO/CEO ("Unifilar") passa a se chamar "Fusões", inclusive o botão no popup do mapa.

## [0.31.0] - 2026-07-30

### Corrigido

- **Regressão da v0.30.0**: clicar nos ícones da toolbar de cima ou da barra inferior do mapa, com uma ferramenta de adicionar equipamento ativa, abria o diálogo de "Novo elemento" na posição do clique. A causa: ao mover essas barras para dentro do `#map` (para centralizar corretamente), o clique nelas passou a vazar para o mapa do Leaflet por baixo. Corrigido bloqueando a propagação de clique/scroll dessas barras para o mapa.

### Adicionado

- Menu de clique direito no mapa (modo edição, com projeto selecionado): adiciona CTO, CEO, Rack ou Torre diretamente no ponto clicado, sem precisar armar a ferramenta na barra lateral primeiro. Cabo não entra nesse menu, já que sempre precisa de origem e destino.

## [0.30.0] - 2026-07-30

### Adicionado

- Camadas do mapa por tipo: além do toggle "Geral", agora dá para ligar/desligar CTO, CEO e Cabos de forma independente, tanto no painel "Camadas" quanto em ícones na barra inferior do mapa.
- Barra inferior do mapa reduzida a ícones (Geral/CTO/CEO/Cabos + Agrupar PPPoE/Agrupar equipamentos), sincronizados com os checkboxes do painel lateral.

### Alterado

- A seção de ligações internas do rack (OLT → DIO) passa a se chamar "Fusões — OLT → DIO", em vez do nome técnico anterior.
- Botões "Excluir" e "Desligar" do diagrama de estrutura do rack/torre ganharam estilo próprio (antes usavam o botão padrão do navegador, sem nenhum destaque visual).

### Corrigido

- A toolbar de visualizar/editar/pesquisar (topo do mapa) e a barra inferior ficavam centralizadas em relação à tela toda, não à área visível do mapa — com a barra lateral aberta, elas apareciam deslocadas para a direita. Agora ficam centralizadas de verdade na área do mapa, em qualquer largura de barra lateral.

## [0.29.2] - 2026-07-30

### Corrigido

- **Crítico**: Visão geral do projetista quebrava com erro 500 assim que existia pelo menos um cabo desenhado com geometria — o cálculo de "km de cabo" não informava explicitamente o tipo de retorno da função de comprimento (`output_field`), o que só falhava com dado real (antes era nunca exercitado com o queryset vazio). Agora o cálculo é explícito e, mesmo que a geometria de algum cabo seja inválida, o dashboard não quebra mais (só mostra 0 km nesse caso).
- Página "Equipamentos": o formulário de "+ Novo equipamento" exigia um campo "Projeto" que nunca era exibido na tela, fazendo o cadastro falhar silenciosamente (sem nenhuma mensagem de erro visível). Editar equipamento existente tinha o mesmo problema.

### Removido

- "+ Novo equipamento" na página "Equipamentos": cadastro de equipamento passa a ser feito só pelo mapa, onde o projeto e a posição já ficam definidos. A página "Equipamentos" continua para ver, editar e excluir.

## [0.29.1] - 2026-07-30

### Corrigido

- **Crítico**: o código de projeto (`NetworkProject.code`) e de rota (`NetworkRoute.code`) era único **globalmente** no banco, entre todas as empresas, em vez de único só dentro de cada empresa. Isso impedia uma empresa nova de criar um projeto com um código (ex.: "CTO 01") já usado por qualquer outra empresa na plataforma, mesmo sendo dados totalmente isolados. Agora a unicidade é por empresa (`company + code`), replicando o mesmo padrão já usado em POP, modelo de cabo e padrão de cores.
- A checagem de "já existe um projeto com esse código" no editor de mapa também comparava contra todas as empresas; agora compara só dentro da empresa do projeto sendo criado.
- Login sempre abria "Minha administração" em vez da Visão geral, mesmo com `LOGIN_REDIRECT_URL` configurado para `/` desde a v0.27.1: o formulário de login tinha um campo oculto `next` com valor fixo `/painel/`, que sempre vencia a configuração. Removido o valor fixo.
- Dropdown de sugestões da busca aparecia praticamente transparente: a variável CSS `--panel`, usada em vários componentes (busca, formulários, acordeões), nunca havia sido definida em `:root` — bug antigo do CSS que só ficou visível com o dropdown flutuando sobre outros cards.
- Card "Dados da empresa" do dashboard do projetista exibia rótulo e valor sobrepostos (ex.: "NorLC-PROJETOS") por reaproveitar uma grade pensada para 3 colunas com apenas 2 elementos.

### Observação

- Migração segura sem necessidade de limpeza de dados: como o código já era único globalmente antes, não podem existir hoje dois registros com o mesmo código — a nova regra (mais permissiva) nunca falha ao ser aplicada.

## [0.29.0] - 2026-07-30

### Adicionado

- Busca ampla e escopada por empresa em "Minha administração": digite e receba sugestões em tempo real de projetos, equipamentos e caixas (CTO/CEO/DIO/OLT/poste), cabos, CPD/POP, OLTs, clientes e logins PPPoE — sem precisar de termo exato, cobrindo toda a base (não só os primeiros 100 registros carregados na tela). Superusuário busca em todas as empresas; cada empresa busca só nos seus dados.
- E-mail (SMTP) por empresa: cada empresa cadastra o próprio servidor de e-mail (host, porta, usuário, senha criptografada, TLS, remetente) em "Minha administração" e pode enviar um e-mail de teste.
- SMTP padrão da plataforma via variáveis de ambiente (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`), testável com o comando nativo `manage.py sendtestemail`. É de uso interno/administrativo — não serve de reserva para empresas sem SMTP próprio.

### Alterado

- Menu lateral perde os atalhos "OLTs e ONUs" e "Integração ERP", que agora só existem dentro de "Minha administração" (evita duplicidade de navegação para a mesma informação).

### Observação

- Sem SMTP próprio configurado, a empresa simplesmente não envia e-mail — não há reserva automática pelo SMTP da plataforma.
- O envio de e-mail de alertas de fato ainda depende do motor de alertas, que continua em desenvolvimento; por enquanto esta integração permite configurar e testar o SMTP.

## [0.28.1] - 2026-07-30

### Adicionado

- "Minha administração" agora tem um item próprio no menu lateral, além do nome do usuário no topo.
- Novo bloco "Configurações da empresa" no topo do painel, com atalhos diretos para Dados da empresa, Minha equipe, Integração ERP (quando aplicável) e Central de alertas.
- A página de dados da empresa (`/painel/primeiro-acesso/`) muda o texto para "Dados da empresa" quando acessada depois do onboarding, em vez de repetir a mensagem de boas-vindas do primeiro acesso.

### Removido

- Seções duplicadas de "Integração ERP" e o aviso genérico de "Alertas" dentro do painel — ambas já têm página própria, agora promovidas para os atalhos de "Configurações da empresa".

### Observação

- SMTP/e-mail de alertas fica para uma próxima etapa: hoje nada no sistema envia e-mail (nem recuperação de senha, nem o motor de alertas, que ainda não existe), então configurar SMTP agora não teria efeito visível.

## [0.28.0] - 2026-07-30

### Adicionado

- Página **Minha equipe** (`/painel/equipe/`), onde um usuário EDIT cadastra novas pessoas da própria empresa com usuário e senha definidos na hora, escolhendo o papel VIEW ou EDIT.
- O usuário principal pode ativar/desativar o acesso de qualquer membro da sua equipe e trocar o papel (VIEW ↔ EDIT) a qualquer momento, sem depender do suporte.
- Atalho "Minha equipe" no dashboard (provedor e projetista) e em "Minha administração", visível apenas para quem tem permissão de edição.

### Observação

- A senha definida para o novo membro passa pelas mesmas validações padrão do Django (tamanho mínimo, não pode ser trivial/numérica). O usuário criado nunca tem acesso ao Django Admin nem a outras empresas.

## [0.27.1] - 2026-07-30

### Alterado

- Login passa a abrir direto a Visão geral (dashboard), em vez do painel técnico "Minha administração".
- Topo da tela mostra apenas o nome do usuário e "Sair"; removidos o atalho "API" e o círculo com iniciais.
- Documentado como configurar um Personal Access Token (ou SSH) no servidor Debian para o `apply` parar de pedir usuário e senha a cada atualização.

### Corrigido

- O gate de primeiro acesso (escolha de tipo de empresa, modo ERP/manual e configuração pendente do IXCSoft) agora também é aplicado à Visão geral e ao mapa, não só ao painel técnico — evita que uma conta com onboarding incompleto "escape" da configuração inicial ao entrar direto pela página principal.

## [0.27.0] - 2026-07-30

### Adicionado

- Tipo de empresa no primeiro acesso: **Provedor** (tem clientes, pode usar ERP ou não) ou **Projetista** (só desenha e mantém projetos de rede, sem clientes e sem opção de ERP).
- Segunda etapa de onboarding exclusiva para provedores, para escolher entre operar com ERP ou sem ERP, separada do cadastro dos dados da empresa.
- Dashboard próprio para empresas projetistas, com indicadores de CTOs, CEOs/caixas de emenda, DIOs, OLTs e quilometragem de cabo desenhada, além de atalho para editar os dados da empresa e abrir o mapa.
- Campo `company_type` no Django Admin de Empresas, para o suporte da plataforma liberar a troca de tipo depois do primeiro acesso (mudança sujeita a plano/custo mensal diferente).

### Corrigido

- `NameError` que impedia usuários não administradores de acessar a etapa de integração ERP (`Company` não estava importado em `apps/core/views.py`).

### Alterado

- Empresas que já haviam concluído o cadastro antes desta versão foram classificadas automaticamente como **Provedor**, preservando o comportamento atual; nenhuma reclassificação manual é necessária.

## [0.26.0] - 2026-07-29

### Adicionado

- Seleção de todos os equipamentos da página e exclusão em lote, respeitando a empresa e a permissão EDIT.
- Cadastro SNMP de OLT com IP, modelo e community armazenada criptografada.
- Próximo slot livre calculado automaticamente ao adicionar uma placa à OLT.

### Alterado

- OLT manual solicita apenas o nome; placas e PONs passam a ser cadastradas individualmente.
- DIO deixa de exibir campos de IP e identificação incompatíveis.
- Ligações internas de rack e torre ficam recolhidas até o operador abrir o diagrama.
- Empresas manuais novas recebem acesso EDIT por padrão e não visualizam opções de ERP.

### Corrigido

- Loop de redirecionamento no primeiro acesso de usuários manuais.
- Logout da plataforma retornando incorretamente ao login técnico do Django.
- Mensagens de conflito da API agora aparecem ao operador, inclusive slot de placa já ocupado.
- Ações de edição e exclusão ocultas e bloqueadas para perfis somente VIEW.

## [0.25.0] - 2026-07-29

### Adicionado

- Placas de OLT individuais por slot, cada uma com sua própria quantidade de PONs.
- Portas configuráveis para switches, APs e rádios: RJ45 100 Mb/1 Gb, SFP 1 Gb, SFP+ 10 Gb e wireless.
- Ligações internas de torre por cobre, fibra ou enlace wireless.
- Perfil de acesso por empresa para usuário manual ou vinculado a ERP.
- Comando seguro e repetível para limpar somente dados importados de uma empresa.

### Alterado

- Editor de rack e torre passou a usar praticamente toda a tela.
- Estrutura interna mostra equipamentos, placas, portas e ligações em uma visão técnica única.
- Cadastro inicial de OLT cria somente a primeira placa; as demais são adicionadas individualmente.

## [0.24.0] - 2026-07-29

### Adicionado
- Inventário real de equipamentos internos de Rack e Torre, substituindo a antiga descrição em texto livre.
- Geração automática das PONs por placa de OLT e das portas de DIO nas capacidades de 12 a 244 portas.
- Ligações internas entre PON da OLT e porta do DIO, com associação opcional ao cabo óptico conectado ao rack.

### Corrigido
- CDOs repetidas entre as fontes de elementos e caixas do IXCSoft agora reaproveitam o mesmo registro e atualizam tipo e coordenadas.
- O modo de visualização limita o menu lateral a projetos e camadas, mantendo todas as ações protegidas pelo modo de edição.
- Os controles de visualizar, editar e pesquisar ficam no topo; a pesquisa só aparece ao clicar na lupa.

## [0.23.0] - 2026-07-29

### Corrigido
- CDOs importados do IXCSoft agora são classificados como CEO/caixa de emenda sem apagar seus vínculos.
- O mapa operacional inicia realmente recolhido no modo de visualização.
- O popup do assinante cruza PPPoE e vínculo óptico para exibir CTO, porta, ONU e serial.

### Adicionado
- Elementos de Rack e Torre no editor do mapa.
- Cadastro da estrutura interna do Rack (OLT/DIO) e da Torre (switch/AP/PTP).

## [0.22.0] - 2026-07-29

### Alterado

- O mapa agora usa apenas três atalhos visuais: visualizar, editar/desenhar e pesquisar.
- A pesquisa permanece recolhida até o operador clicar na lupa.
- No modo de visualização, CTOs, CEOs, postes, reservas e cabos exibem somente informações, sem ações ou movimentação.
- A sincronização completa passa a respeitar o intervalo configurado por empresa; o estado PPPoE é atualizado separadamente a cada cinco minutos.
- ONUs do IXC são consideradas somente quando possuem login/cliente relacionado.

### Removido

- Cabos detectados pelo nome no inventário IXC não são mais importados automaticamente. Cabos devem ser identificados e desenhados manualmente.
- Cabos IXC pendentes, sem geometria, criados pela versão anterior são removidos na migração.

Todas as mudanças relevantes do projeto são registradas neste arquivo.

## [Não lançado]

### Planejado

- Integrar as telas de equipamentos ao novo layout compartilhado
- Implementar coleta SNMP real em OLTs FiberHome
- Criar perfis de OIDs por modelo e firmware
- Implementar descoberta de portas PON e ONUs

## [0.21.0] - 2026-07-29

### Adicionado

- Importação de itens do `df_elemento` cujo nome/tipo contém “CABO” como cabo óptico aguardando traçado.
- Identificação automática da quantidade de fibras em nomes como `CABO 6FO`, `12 F.O` e `24 fibras`.
- Seletor para escolher e desenhar no mapa um cabo importado que ainda não possui geometria.
- Barra de modos do mapa com ações de visualizar, editar, desenhar e pesquisar.

### Corrigido

- CDOs e caixas de atendimento permanecem no grupo de CTOs, enquanto CEO, CF e caixas de emenda passam a ser classificadas como caixas de emenda.
- Elementos repetidos entre `rad_caixa_ftth` e `df_elemento` deixam de aparecer duplicados quando o nome e o projeto coincidem.
- Uma nova sincronização preserva o traçado manual já desenhado para um cabo importado.

### Observação

- Os exemplos de API IXCSoft fornecidos não incluem geometria, origem ou destino em `df_elemento`; por isso os cabos entram no inventário sem linha até serem desenhados ou importados por KML/KMZ.

## [0.20.0] - 2026-07-29

### Adicionado

- Acompanhamento ao vivo da sincronização, separado por etapa e atualizado a cada 100 registros.
- Amostras dos erros de cada etapa no relatório.
- Atualização automática da tela enquanto a importação estiver em execução.
- Geração dos acessos operacionais PPPoE usados pelos indicadores do dashboard.

### Corrigido

- Bloqueio de sincronizações simultâneas da mesma integração.
- Clientes sem contrato ativo são removidos quando a opção correspondente estiver marcada.
- Execuções antigas presas em “Executando” são encerradas durante a atualização.

### Documentado

- Cabos e rotas não são importados sem o endpoint e a geometria correspondentes do IXCSoft.

## [0.19.1] - 2026-07-29

### Corrigido

- Dashboard de empresas não exibe mais ONUs, OLTs, clientes, alertas ou sincronizações de terceiros.
- Reset de teste remove integralmente os dados vinculados à Nic Fibra/Eduardo.
- Logo centralizada no painel esquerdo da tela de login.

### Adicionado

- Botão **Sincronizar agora** e relatório das dez últimas execuções da integração ERP.
- Rótulos em português no formulário do IXCSoft.

## [0.19.0] - 2026-07-29

### Adicionado

- Primeiro acesso com cadastro obrigatório de nome, contato, endereço e CPF/CNPJ.
- Escolha entre vincular um ERP ou operar integralmente sem ERP.
- Página própria de alertas com isolamento por empresa.

### Alterado

- Integração ERP e Alertas agora abrem telas funcionais próprias.
- O acesso de infraestrutura abre diretamente a seção correta do painel.
- A configuração ERP da Nic Fibra Telecom é reiniciada uma única vez para o teste de onboarding.

## [0.18.1] - 2026-07-29

### Corrigido

- A opção de importar elementos do mapa agora sincroniza efetivamente o endpoint
  `df_elemento` do IXCSoft e relaciona os registros ao projeto da empresa.

## [0.18.0] - 2026-07-29

### Adicionado

- Assistente obrigatório de integração ERP no primeiro acesso de empresas com permissão EDIT.
- Seleção das rotinas IXCSoft: clientes, contratos ativos, PPPoE, projetos e CTOs.
- Cadastro de CPD/POP por latitude e longitude, GPS do navegador ou busca visual no mapa.
- Relação de múltiplos contratos por cliente e vínculo do login PPPoE ao contrato correspondente.

### Alterado

- Dados sincronizados do IXCSoft agora são isolados por empresa.
- Atalhos operacionais deixaram de encaminhar usuários de empresas ao Django Admin.
- Ações sensíveis da API exigem permissão EDIT; usuários VIEW permanecem somente leitura.

### Segurança

- Token do ERP continua criptografado e não é devolvido pela API.

## [0.17.0] - 2026-07-29

### Adicionado

- Área operacional para usuários EDIT criarem CPD/POP, OLT e DIO sem acessar o
  Django Admin.
- Formulários da plataforma limitados às empresas e projetos vinculados à conta.
- Listagem integrada de CPDs, OLTs e DIOs no painel da empresa.
- Atalhos para criação de infraestrutura e edição do projeto no mapa.

### Segurança

- Empresas passam a ter somente os níveis VIEW e EDIT.
- ADMIN fica reservado exclusivamente ao superusuário proprietário da plataforma.
- Telas de equipamentos agora filtram registros pela empresa e validam permissão
  EDIT antes de criar, alterar ou excluir.

### Melhorado

- Login redesenhado com composição moderna, responsiva e identidade da plataforma.
- Formulários de infraestrutura seguem o mesmo padrão visual do painel operacional.

## [0.16.1] - 2026-07-29

### Corrigido

- Login de usuários VIEW, EDIT e ADMIN da empresa agora utiliza a autenticação da
  plataforma e não exige a permissão interna “membro da equipe” do Django.
- Categorias da Central de Controle permanecem realmente recolhidas até o clique.
- Menu técnico lateral inicia fechado e continua disponível pelo botão de expansão.
- Atividade recente permanece disponível em todas as páginas administrativas sem
  sobrepor os atalhos do cabeçalho.

### Adicionado

- Botão seguro para encerrar a sessão no painel operacional.

## [0.16.0] - 2026-07-29

### Adicionado

- Login obrigatório desde a entrada da plataforma.
- Painel operacional próprio para cada empresa, com projetos, equipamentos e cabos autorizados.
- Pesquisa central no painel do cliente limitada ao conteúdo que sua conta pode acessar.
- Administração da empresa baseada nos níveis VIEW, EDIT e ADMIN.

### Melhorado

- Atividade recente do painel técnico transformada em sino recolhido.
- Categorias administrativas fechadas por padrão e abertas sob demanda.
- Menu lateral técnico removido da página inicial para reduzir poluição visual.
- Pesquisa moderna no topo da Central de Controle.
- Links do painel da empresa abrem o projeto correto diretamente no mapa.

### Segurança

- Acessos, elementos e cabos do mapa são filtrados no servidor pela empresa do usuário.
- Operações principais de elementos validam o nível de edição da empresa.

## [0.15.0] - 2026-07-29

### Adicionado

- Níveis de acesso multiempresa VIEW, EDIT e ADMIN.
- Vínculo explícito entre usuários e empresas, com ativação e desativação de acesso.
- Central administrativa organizada por empresas, projetos, rede óptica e integrações.
- Atalhos compactos separados para poste e visibilidade dos nomes no mapa.

### Segurança

- Django Admin restrito ao superadministrador da plataforma.
- Projetos filtrados pelas empresas liberadas ao usuário.
- Usuários VIEW não podem alterar ou excluir projetos.
- Criação e importação de projetos validam a empresa e o nível EDIT/ADMIN.

### Corrigido

- Camada de satélite deixa de solicitar o nível rural sem cobertura da Esri e amplia
  a última imagem disponível, evitando os blocos “Map data not yet available”.

## [0.14.3] - 2026-07-29

### Adicionado

- Pesquisa central no mapa com modos separados para endereço e estrutura do projeto.
- Busca por CTO, CEO, OLT, DIO, poste, cabo, nome e código dentro do projeto selecionado.
- Lista de resultados com enquadramento automático do equipamento ou do traçado completo do cabo.
- Botão para centralizar o mapa pela localização GPS do dispositivo.
- Camada híbrida Esri com imagem de satélite, nomes de lugares e referências viárias.
- Alternância entre satélite híbrido, satélite limpo e mapa de ruas.

### Melhorado

- Zoom visual máximo ampliado para o nível 23 com sobrezoom das fontes disponíveis.

## [0.14.2] - 2026-07-29

### Melhorado

- Formulários de CTO, CEO, reservas e splitters agora usam modais internos, sem caixas de entrada nativas do navegador.
- Administração recebeu navegação por atalhos, melhor hierarquia visual, formulários e listagens mais legíveis.
- Mapas GIS administrativos passam a abrir centralizados na região de Imbaú.

### Adicionado

- Localização rápida no cadastro de CPD e DIO por endereço, GPS ou coordenadas.
- DIO sem coordenadas próprias herda automaticamente a localização do CPD.
- CPD sem coordenadas próprias pode herdar uma localização existente do projeto.
- Atalhos diretos no admin para visão geral, mapa, projetos, CPDs, OLTs e DIOs.

## [0.14.1] - 2026-07-29

### Corrigido

- A infraestrutura do poste agora lista somente cabos que passam a até 8 metros de sua posição.
- CTOs e CEOs exibidas no poste agora são apenas as realmente instaladas nele.
- Reservas técnicas só podem ser criadas quando existe um cabo passando pelo poste.

### Adicionado

- Ações contextuais no poste para instalar uma nova CTO, instalar uma nova CEO e criar reserva.
- Ícones vetoriais padronizados no editor, nos atalhos recolhidos e nos marcadores do mapa.
- Novo desenho de poste no mapa, substituindo o marcador textual `P`.

## [0.14.0] - 2026-07-29

### Corrigido

- A mesma fibra física pode ser terminada uma vez em cada extremidade do cabo.
- O falso conflito “fibra já utilizada” deixa de bloquear ligações em caixas diferentes.
- Saídas dos splitters voltam a ser identificadas como `F1`, `F2` etc.

### Adicionado

- CPD/POP único por projeto.
- OLT vinculada ao CPD com modo manual ou descoberta SNMP.
- Cadastro de placas da OLT e geração das respectivas portas PON.
- Potência de saída em dBm por porta PON.
- Geração automática de bandeja e portas do DIO.
- Gestão, pelo mapa, dos cabos que passam em cada poste.
- Vínculo de CTOs e CEOs instaladas em postes.

## [0.13.2] - 2026-07-29

### Corrigido

- O mapa agora exibe a mensagem devolvida pelo Google em vez de ocultá-la atrás
  de um erro HTTP 502 genérico.

## [0.13.1] - 2026-07-29

### Corrigido

- Sessão e blocos do Google Map Tiles agora são solicitados pelo backend.
- A restrição de IP da chave passa a validar o IP público do servidor, não o
  computador do operador.
- A chave da API não é mais enviada ao navegador.

## [0.13.0] - 2026-07-29

### Adicionado

- Configuração administrativa do Google Map Tiles com chave criptografada.
- Camada oficial Google Satélite 2D no seletor do mapa.
- Escolha da camada padrão pelo painel administrativo.

### Segurança

- A chave não é gravada no código-fonte ou no repositório.

### Resiliência

- O satélite alternativo permanece disponível e é usado automaticamente quando
  a sessão do Google não puder ser criada.

## [0.9.4] - 2026-07-29

### Corrigido

- Clique diretamente sobre o cabo agora registra a reserva técnica
- Fibras e tubos já existentes são remapeados para suas posições ABNT; não é necessário excluir cabos

### Adicionado

- Configuração de quantidade de bandejas na CEO
- Splitters opcionais por bandeja com proporção configurável
- Visualização unifilar inicial das bandejas, fusões e splitters da CEO

## [0.10.0] - 2026-07-29

### Adicionado

- Edição de metragem, posição e exclusão de reservas técnicas
- Conversão de uma reserva existente em CTO ou CEO
- Inserção direta de CTO/CEO no meio de um cabo
- Divisão automática do cabo em dois trechos ligados ao novo elemento
- Editor unifilar da CEO com fibras dos cabos conectados
- Criação de fusões por arrastar uma fibra sobre outra e escolha da bandeja
- Remoção de fusões no próprio unifilar

## [0.10.1] - 2026-07-29

### Corrigido

- Fusões não exibem mais IDs internos como “Fibra 122 → Fibra 134”
- Identificação agora usa cabo, número operacional e cor da fibra

### Alterado

- Unifilar da CEO redesenhado como grafo óptico com cabos, portas, bandejas e linhas coloridas
- Ligações podem ser feitas clicando em duas portas ou arrastando uma fibra sobre outra

## [0.10.2] - 2026-07-29

### Adicionado

- Splitters aparecem dentro de suas respectivas bandejas no grafo
- Porta de entrada e portas de saída numeradas para cada splitter
- Ligação de fibra do cabo à entrada do splitter
- Ligação das saídas do splitter às fibras dos cabos derivados
- Linhas específicas para alimentação e derivações

### Alterado

- Popup do unifilar ampliado para até 96% da tela e área de desenho expandida

## [0.10.3] - 2026-07-29

### Corrigido

- Inicialização bloqueada pelo `admin.E040` após adicionar portas de splitter
- Busca automática do painel administrativo agora encontra splitters por bandeja, CEO, nome e código

## [0.11.0] - 2026-07-29

### Adicionado

- Cabos e bandejas podem ser arrastados livremente no canvas unifilar
- Posições do desenho são persistidas por CEO
- Inclusão, alteração e exclusão individual de splitters em cada bandeja
- Remoção de ligações das entradas e saídas dos splitters
- Cadastro de OLT diretamente no mapa
- Seleção da OLT de origem e animação do caminho da luz nos cabos
- Destaque visual da direção origem → destino da rede

## [0.12.5] - 2026-07-29

### Corrigido

- Fibras e saídas ocupadas são bloqueadas antes da requisição, evitando conflitos 409 repetidos.
- Mensagens do unifilar agora aparecem dentro da própria janela.
- Popup do cabo é fechado ao editar ou mover o traçado.

### Alterado

- Portas do splitter usam `S1`, `S2` etc. para diferenciar saída de splitter de fibra do cabo.

## [0.12.4] - 2026-07-29

### Corrigido

- O mapa não solicita mais tiles inexistentes nos níveis máximos.
- A última imagem disponível é ampliada até o zoom 22, evitando blocos cinza.

## [0.12.3] - 2026-07-29

### Adicionado

- Expansão individual e persistente para mostrar todas as fibras de cada cabo.
- Controles inferiores para agrupar ou separar PPPoE e equipamentos.

### Alterado

- Satélite sem API e sem cobrança definido como mapa inicial.
- Camadas simplificadas para clientes PPPoE online e offline.
- Painel duplicado de fusões removido do rodapé do unifilar.

## [0.12.2] - 2026-07-29

### Adicionado

- Zoom persistente no unifilar com ampliar, reduzir e ajustar à tela.
- Atalhos de cabo, CTO, CEO, OLT e nomes no menu recolhido.
- Linhas bicolores para representar fusões entre fibras de cores diferentes.

### Alterado

- Janela do unifilar ampliada para praticamente toda a tela.
- Splitter vertical com entrada à esquerda e saídas empilhadas à direita.
- Saídas do splitter fazem transição da cor de entrada para a fibra de destino.

## [0.12.1] - 2026-07-29

### Adicionado

- CTOs agora possuem o mesmo editor unifilar das CEOs.
- Passagem direta permite continuar fibras para o próximo cabo na CTO.
- Splitters da CTO aceitam entrada e derivações para fibras de outros cabos.

### Alterado

- Splitters são exibidos verticalmente, com entrada superior e saídas inferiores.
- A seta luminosa acompanha o ângulo real de cada trecho do cabo.
- CTOs existentes recebem a estrutura óptica automaticamente.

## [0.12.0] - 2026-07-29

### Adicionado

- Desenho de cabos iniciando e terminando diretamente em OLT, CEO ou CTO.
- Controle para mostrar ou ocultar nomes dos cabos e equipamentos.
- Seleção simplificada de cabo pela quantidade de fibras.

### Alterado

- O fluxo luminoso só atravessa uma CEO quando existe fusão real no unifilar.
- Cabos de entrada são posicionados à esquerda e cabos de saída à direita no unifilar.
- O modelo selecionado define automaticamente a quantidade de fibras e sugere um nome padronizado.

## [0.11.2] - 2026-07-29

### Corrigido

- Linhas de fusão e de splitter agora podem ser clicadas para excluir e redesenhar.
- Ligações usam a cor ABNT da fibra de origem e, após o splitter, da fibra de destino.
- Fluxo óptico no mapa ganhou seta luminosa animada indicando o sentido.
- Marcadores de CTO, CEO e OLT agora possuem ícones próprios e identificação legível.

## [0.11.1] - 2026-07-29

### Corrigido

- Uma fibra não pode mais participar de duas ligações simultâneas
- Ligações duplicadas existentes são limpas automaticamente pela migração
- Bandejas não são mais repetidas abaixo do canvas

### Adicionado

- Partículas luminosas animadas sobre o cabo mostram o deslocamento do sinal
- Bandeja selecionada diretamente no canvas para receber a fusão
- Linhas curvas, retas ou ortogonais com preferência persistente
- Exclusão de fusão clicando diretamente na linha do desenho

## [0.9.3] - 2026-07-29

### Adicionado

- Edição do traçado por vértices arrastáveis diretamente no mapa
- Encaixe automático das pontas em CTOs, CEOs e demais elementos próximos
- Reserva técnica posicionada no mapa com metragem identificada
- Símbolo próprio de bobina para reservas
- Sequência de cores ABNT: verde, amarelo, branco, azul, vermelho, violeta, marrom, rosa, preto, cinza, laranja e água

### Alterado

- Catálogos ópticos existentes são migrados para a ordem ABNT

## [0.9.2] - 2026-07-29

### Adicionado

- Seleção do cabo conectado e da fibra que alimenta o splitter ao editar a CTO
- Vínculo persistente entre cabo, fibra, CTO e entrada do splitter
- Exibição do nome do cabo, número e cor real da fibra no unifilar
- Atualização automática do estado e da contagem de fibras utilizadas

## [0.9.1] - 2026-07-29

### Adicionado

- Edição de postes, CTOs, CEOs e cabos diretamente pelos pop-ups do mapa
- Conexão da origem e do destino do cabo aos elementos do mesmo projeto
- Encaixe automático das pontas do cabo e acompanhamento ao mover o elemento
- Configuração de capacidade, proporção do splitter e portas ao criar ou editar CTO
- Cadastro persistente de splitters e portas de atendimento
- Visualização unifilar de cada CTO com o estado individual das portas
- Exclusão de cabos diretamente no mapa

## [0.9.0] - 2026-07-29

### Adicionado

- Projetos de rede com nome, código, status, empresa e cor
- Projeto obrigatório para novos elementos e cabos
- Menu do mapa recolhível e redimensionável
- Camadas independentes de estrutura, clientes online, offline e sem estado
- Cadastro de postes, CTOs e CEOs clicando diretamente no mapa
- Movimentação de elementos por arrastar e soltar
- Desenho de cabos por múltiplos pontos
- Importação de arquivos KML e KMZ para o projeto selecionado
- Alternância entre mapa convencional e imagem de satélite
- Resumos de elementos, cabos, rotas e clientes

### Segurança

- Criação, alteração, importação e exclusão exigem usuário autenticado
- Endpoints de leitura permanecem disponíveis para o mapa operacional

## [0.8.9] - 2026-07-29

### Corrigido

- Logo centralizada no eixo visual do menu lateral
- Favicon local permitido sem bloquear o comando `apply`

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
