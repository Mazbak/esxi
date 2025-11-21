# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('esxi', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('backups', '0004_backupjob_backup_mode'),
    ]

    operations = [
        # Modifier le choix par défaut pour backup_mode
        migrations.AlterField(
            model_name='backupjob',
            name='backup_mode',
            field=models.CharField(
                max_length=50,
                choices=[('ovf', 'OVF Export (Standard format - Restorable)')],
                default='ovf'
            ),
        ),
        # Créer le modèle SnapshotSchedule
        migrations.CreateModel(
            name='SnapshotSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frequency', models.CharField(
                    choices=[('hourly', 'Hourly'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
                    default='daily',
                    max_length=50
                )),
                ('retention_count', models.PositiveIntegerField(default=7, help_text='Nombre de snapshots à conserver')),
                ('include_memory', models.BooleanField(default=False, help_text='Inclure la mémoire RAM dans le snapshot')),
                ('is_active', models.BooleanField(default=True)),
                ('last_run', models.DateTimeField(blank=True, null=True)),
                ('next_run', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='snapshot_schedules', to=settings.AUTH_USER_MODEL)),
                ('virtual_machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='snapshot_schedules', to='esxi.virtualmachine')),
            ],
            options={
                'verbose_name': 'Snapshot Schedule',
                'verbose_name_plural': 'Snapshot Schedules',
            },
        ),
        # Créer le modèle Snapshot
        migrations.CreateModel(
            name='Snapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('snapshot_name', models.CharField(max_length=255)),
                ('snapshot_id', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('creating', 'Creating'), ('completed', 'Completed'), ('failed', 'Failed')],
                    default='pending',
                    max_length=50
                )),
                ('include_memory', models.BooleanField(default=False)),
                ('size_mb', models.FloatField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='snapshots', to=settings.AUTH_USER_MODEL)),
                ('schedule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='snapshots', to='backups.snapshotschedule')),
                ('virtual_machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='esxi.virtualmachine')),
            ],
            options={
                'verbose_name': 'Snapshot',
                'verbose_name_plural': 'Snapshots',
                'ordering': ['-created_at'],
            },
        ),
    ]
