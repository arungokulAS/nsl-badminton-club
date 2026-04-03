from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournamentregistration',
            name='team_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RemoveField(
            model_name='tournamentregistration',
            name='player1_name',
        ),
        migrations.RemoveField(
            model_name='tournamentregistration',
            name='player2_name',
        ),
        migrations.RemoveField(
            model_name='tournamentregistration',
            name='contact_phone',
        ),
        migrations.RemoveField(
            model_name='tournamentregistration',
            name='contact_email',
        ),
        migrations.RemoveField(
            model_name='tournamentregistration',
            name='city',
        ),
        migrations.RemoveField(
            model_name='tournamentregistration',
            name='notes',
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player1_first_name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player1_last_name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player1_category',
            field=models.CharField(default='A', max_length=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player1_contact_number',
            field=models.CharField(default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player1_email',
            field=models.EmailField(default='placeholder@example.com', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player1_city',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player2_first_name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player2_last_name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player2_category',
            field=models.CharField(default='A', max_length=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player2_contact_number',
            field=models.CharField(default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player2_email',
            field=models.EmailField(default='placeholder@example.com', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='player2_city',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='emergency_contact_name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='emergency_contact_number',
            field=models.CharField(default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tournamentregistration',
            name='emergency_contact_relation',
            field=models.CharField(default='Friend', max_length=20),
            preserve_default=False,
        ),
    ]
