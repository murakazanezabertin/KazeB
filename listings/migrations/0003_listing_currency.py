from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_listing_views_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="currency",
            field=models.CharField(
                choices=[("RWF", "RWF"), ("USD", "$")],
                default="RWF",
                max_length=3,
            ),
        ),
    ]
