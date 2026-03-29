from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedule", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="round",
            name="points_per_set",
            field=models.PositiveIntegerField(default=21),
        ),
        migrations.AddField(
            model_name="round",
            name="sets_per_match",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="round",
            name="settings_locked",
            field=models.BooleanField(default=False),
        ),
    ]
