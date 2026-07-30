# Changelog

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
