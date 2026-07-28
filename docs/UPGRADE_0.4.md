# Atualização para 0.4.0

1. Substitua os arquivos do repositório pelos arquivos do ZIP.
2. Gere `FIELD_ENCRYPTION_KEY` com o comando documentado no README.
3. Atualize `.env` sem publicar esse arquivo.
4. Execute `makemigrations` e `migrate` dentro do container web.
5. Execute os testes.
6. Cadastre a configuração IXC pelo admin.
7. Teste a conexão antes de iniciar a sincronização.

> Como ainda não existe banco de produção oficial do projeto, as migrations devem ser geradas no ambiente Docker após esta atualização. Isso evita congelar migrations incorretas sem validar a versão real do Django/PostGIS usada no deploy.
