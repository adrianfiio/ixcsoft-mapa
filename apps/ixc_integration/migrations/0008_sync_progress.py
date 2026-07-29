from django.db import migrations, models


def close_stale_runs(apps, schema_editor):
    Execution = apps.get_model("ixc_integration", "IXCSyncExecution")
    Execution.objects.filter(status="running").update(
        status="failed",
        current_stage="Interrompido pela atualização",
        error_message="A execução anterior não apresentou conclusão e foi encerrada.",
    )


class Migration(migrations.Migration):
    dependencies = [("ixc_integration", "0007_purge_nic_fibra_test_data")]
    operations = [
        migrations.AddField(model_name="ixcsyncexecution", name="current_stage", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="ixcsyncexecution", name="stage_results", field=models.JSONField(blank=True, default=dict)),
        migrations.RunPython(close_stale_runs, migrations.RunPython.noop),
    ]
