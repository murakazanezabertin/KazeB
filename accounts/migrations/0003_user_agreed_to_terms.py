from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_profile_picture"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="agreed_to_terms",
            field=models.BooleanField(
                default=False,
                help_text="Yagaragaje ko yemeye amabwiriza n'amategeko igihe yiyandikishaga.",
                verbose_name="Yemeye amabwiriza",
            ),
        ),
    ]
