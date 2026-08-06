from django.db import migrations


class Migration(migrations.Migration):
    # No-op: 0001_initial já cria estes 12 campos diretamente em AccessPoint
    # (ixc_customer_id, ixc_contract_id, onu_mac, cto_ixc_id, ftth_port,
    # concentrator_id, concentrator, interface_transmission, connection_type,
    # last_connection_start, last_connection_end, disconnect_reason).
    # As AddField originais desta migration duplicavam esses campos e
    # quebravam qualquer `migrate` num banco novo com "column already
    # exists". Em produção esta migration já está registrada como aplicada
    # (django_migrations rastreia só o nome, não o conteúdo), então esta
    # troca não reaplica nada nem afeta bancos existentes — só corrige o
    # caminho de banco novo/disaster recovery. Mantido como arquivo (não
    # apagado) porque billing.0001, ixc_integration.0007 e network_map.0007
    # dependem dele pelo nome.
    dependencies = [
        ("access", "0001_initial"),
    ]

    operations = []
