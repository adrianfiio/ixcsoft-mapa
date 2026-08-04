# MAP v0.75.12 — ligações técnicas, PTP e busca GPS

## Objetivo

Consolidar o uso real do Canvas de Rack/Torre depois da estabilização da v0.75.11.

## OLT e DIO

- Placas PON da OLT passam a ser exibidas como linhas horizontais.
- Cada placa PON possui uma canaleta visual abaixo para passagem dos cordões.
- O desenho mantém a OLT atual; não cria sistema de módulos separado.
- Hover em uma porta informa se ela está livre ou para onde está ligada.
- Cordões OLT → DIO usam rota ortogonal arredondada com canal lateral.

## Ligações e DROP

- Área de clique das portas foi ampliada sem aumentar o conector visual.
- Destinos compatíveis recebem destaque durante a ligação.
- Duplo clique na ligação cria a dobra no ponto exato clicado.
- Pontos de dobra podem ser arrastados e removidos.
- DROP pode terminar em DIO, PTO ou porta PON de ONU/ONT.
- Terminações exibem conector APC verde ou UPC azul.

## Notas

- Arrastar, editar e excluir passam a salvar no `container_layout_v3`.

## Enlace PTP

- Clique na porta Wireless de um rádio PTP abre confirmação.
- O usuário escolhe a torre, o equipamento e a porta Wireless de destino.
- O enlace é persistido como ligação wireless e exibido no mapa por linha fina tracejada.
- A linha pode ser removida pelo popup do mapa.

## Busca

A busca reconhece coordenadas digitadas diretamente, por exemplo:

```text
-24.453718, -50.752968
-24,453718 -50,752968
```

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum sistema de módulos de OLT foi criado nesta versão.
