# Generated migration for game detection fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_configuration'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='game_override',
            field=models.CharField(blank=True, help_text='Manual game override (overrides auto-detection)', max_length=50),
        ),
        migrations.AddField(
            model_name='configuration',
            name='detected_game',
            field=models.CharField(blank=True, help_text='Auto-detected game from ROM', max_length=50),
        ),
        migrations.AddField(
            model_name='configuration',
            name='detection_source',
            field=models.CharField(default='default', help_text='Source of game detection: auto, manual, or default', max_length=20),
        ),
    ]