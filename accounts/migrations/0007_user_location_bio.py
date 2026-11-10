from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_emailverification"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="location",
            field=models.CharField(blank=True, max_length=150, verbose_name="Aho uherereye"),
        ),
        migrations.AddField(
            model_name="user",
            name="bio",
            field=models.TextField(blank=True, max_length=500, verbose_name="Ibyo wivugaho"),
        ),
    ]
