from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_agreed_to_terms"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            # `default=True` here only backfills existing rows at
            # migrate-time (accounts that were already signing up and
            # using the site before this feature existed shouldn't
            # suddenly be locked out). New signups get False, which
            # comes from the field definition in models.py, not from
            # this one-off migration default.
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Yakanze umurongo wo kwemeza wo muri imeli ye. Ntabwo ashobora "
                    "kwinjira kugeza iyi imeli yemejwe."
                ),
                verbose_name="Imeli yemejwe",
            ),
        ),
    ]
