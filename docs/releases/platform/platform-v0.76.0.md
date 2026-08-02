# Plataforma v0.76.0

Ponto de partida da trilha de release separada da plataforma.
Corresponde exatamente à v0.76.0 já publicada no changelog/release
global antes desta separação — conteúdo técnico completo em
[docs/releases/v0.76.0.md](../v0.76.0.md).

Resumo: correção de arquitetura do financeiro — quem é cobrado é a
empresa cliente (Provedor ISP ou Projetista), não os assinantes de
internet de cada provedor. Painel Superadmin exclusivo pra cadastro e
gestão de empresa (assinatura, cobrança manual, pagamento, status:
ativar/bloquear/cancelar/desativar/excluir). Painel do cliente
(Provedor/Projetista) só consulta o próprio financeiro — sem cadastro
de cliente próprio, mesma regra de acesso EDIT/VIEW de sempre.
Liberação de confiança (+2 dias de acesso, 1 vez por mês, validado no
backend). Bloqueio de acesso por assinatura com fail-safe: empresa sem
assinatura cadastrada nunca é bloqueada.

Junto com esta versão entrou a separação de versionamento em si:
`PLATFORM_VERSION`/`MAP_VERSION` independentes, `CHANGELOG_PLATFORM.md`/
`CHANGELOG_MAP.md`, `VERSIONS.md`, e as pastas `docs/releases/platform/`
e `docs/releases/map/` — ver [VERSIONS.md](../../../VERSIONS.md).
