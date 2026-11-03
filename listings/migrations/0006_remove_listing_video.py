from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0005_favorite"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="listing",
            name="video",
        ),
    ]
