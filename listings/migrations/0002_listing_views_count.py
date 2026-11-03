from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="views_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
