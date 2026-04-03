from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_update_registration_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentregistration',
            name='declaration_confirmed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='media_consent',
            field=models.CharField(default='do_not_agree', max_length=20),
        ),
    ]
