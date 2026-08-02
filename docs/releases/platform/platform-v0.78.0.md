# Plataforma v0.78.0

Gestão de empresa e equipe pelo Superadmin: uma página nova, "Editar
empresa", que junta cadastro e equipe/acessos de qualquer empresa num
lugar só — ao lado do Financeiro e do Gateway que já existiam por
empresa.

## Entrega

- Página nova (`painel/plataforma/empresas/<id>/editar/`), só
  Superadmin, com link próprio na "Visão da plataforma" e cruzado nas
  páginas de Financeiro e Gateway da mesma empresa.
- Editar cadastro de uma empresa já existente: nome, nome fantasia,
  documento, contato, endereço, tipo (Provedor/Projetista) e modo de
  integração (ERP/manual). Diferente da tela de primeiro acesso
  (self-service), o tipo da empresa **não fica travado** aqui — só o
  Superadmin pode mudar o tipo depois de definido.
- Equipe e acessos da empresa:
  - adicionar membro (mesmo formulário/validação já usado no
    self-service);
  - trocar papel (VIEW ↔ EDIT);
  - ativar/desativar;
  - **redefinir senha** — novidade: não existia em lugar nenhum do
    sistema, nem self-service;
  - **excluir de vez** — novidade, única exceção à filosofia
    não-destrutiva do resto do sistema (que só desativa). Apaga o
    usuário Django e o vínculo com a empresa. Com guarda de segurança:
    se o mesmo usuário também tiver vínculo com outra empresa, a
    exclusão é recusada com uma mensagem explicando o motivo, pra não
    tirar o acesso dele de um lugar que não é esta empresa.

## Dados e segurança

- Nenhum model novo, nenhuma migration.
- Verificado antes de implementar `excluir`: toda referência a usuário
  no resto do banco usa `on_delete=SET_NULL` (`Payment.recorded_by`,
  `TrustRelease.requested_by`, `AlertEvent.acknowledged_by`,
  `CompanyDashboardLayout.updated_by`, `PlatformDashboardLayout.updated_by`,
  `NetworkProject.created_by`) — nenhuma fatura, pagamento, alerta ou
  histórico é apagado ao excluir um usuário, só perde a atribuição
  ("quem fez"). A única FK em cascata é `CompanyMembership.user`, que é
  justamente o vínculo que deve sumir junto.
- Só Superadmin acessa (mesma guarda de todas as páginas
  `painel/plataforma/...`).

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/core/forms.py apps/core/views.py config/urls.py`.
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` balanceadas
  nos templates tocados.
- `git diff --check` sem conflitos/espaço em branco.
- Renderização real da página, o fluxo completo de edição/equipe e a
  guarda de exclusão contra empresa dependem do deploy no servidor —
  não é possível validar aqui.
