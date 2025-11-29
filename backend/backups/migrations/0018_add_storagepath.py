# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0017_add_export_format_to_ovfexportjob'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoragePath',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Nom descriptif du chemin (ex: 'NAS Principal', 'Backup Mensuel')", max_length=100, unique=True)),
                ('path', models.CharField(help_text='Chemin complet (ex: /mnt/backups, \\\\serveur\\partage, /mnt/nfs-share)', max_length=500)),
                ('storage_type', models.CharField(choices=[('local', 'Disque local'), ('smb', 'Partage SMB/CIFS'), ('nfs', 'Partage NFS'), ('iscsi', 'Disque iSCSI'), ('other', 'Autre')], default='local', help_text='Type de stockage', max_length=20)),
                ('description', models.TextField(blank=True, help_text='Description optionnelle du chemin de sauvegarde')),
                ('is_active', models.BooleanField(default=True, help_text='Chemin actif et utilisable')),
                ('is_default', models.BooleanField(default=False, help_text='Chemin par défaut proposé dans les formulaires')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Chemin de sauvegarde',
                'verbose_name_plural': 'Chemins de sauvegarde',
                'ordering': ['-is_default', 'name'],
            },
        ),
    ]
