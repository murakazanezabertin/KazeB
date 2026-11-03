from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0003_listing_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="video",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="listings/videos/",
                verbose_name="Videwo",
            ),
        ),
    ]
