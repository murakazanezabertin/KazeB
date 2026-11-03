import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Backs up the database (as a JSON fixture via dumpdata) and the "
        "media/ folder into a single timestamped .zip under backups/. "
        "Run this on a schedule (e.g. a daily cron job) in production:\n\n"
        "  0 3 * * * cd /path/to/kazeb && /path/to/venv/bin/python manage.py backup_data\n\n"
        "This is a starting point, not a full disaster-recovery solution -- "
        "for a real production database, prefer your database provider's "
        "own backup/snapshot feature (e.g. managed Postgres automatic "
        "backups) over dumpdata, which doesn't scale well to large "
        "databases and doesn't capture things like sequence state as "
        "reliably as a native pg_dump. This command still doesn't COPY "
        "the backup off this server for you -- upload backups/ to S3, "
        "another server, etc. or the backup is only as safe as this disk."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            type=int,
            default=14,
            help="Number of most recent backups to keep (older ones are deleted). Default: 14.",
        )

    def handle(self, *args, **options):
        backups_dir = Path(settings.BASE_DIR) / "backups"
        backups_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        work_dir = backups_dir / f"kazeb-backup-{timestamp}"
        work_dir.mkdir()

        self.stdout.write("Dumping database...")
        dump_path = work_dir / "database.json"
        with open(dump_path, "w", encoding="utf-8") as f:
            call_command(
                "dumpdata",
                exclude=["contenttypes", "auth.permission", "sessions.session", "admin.logentry"],
                indent=2,
                stdout=f,
            )

        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            self.stdout.write("Copying media files...")
            shutil.copytree(media_root, work_dir / "media")

        self.stdout.write("Compressing...")
        archive_path = shutil.make_archive(str(work_dir), "zip", root_dir=work_dir)
        shutil.rmtree(work_dir)

        self.stdout.write(self.style.SUCCESS(f"Backup written to {archive_path}"))

        keep = options["keep"]
        existing = sorted(backups_dir.glob("kazeb-backup-*.zip"), reverse=True)
        for old_backup in existing[keep:]:
            old_backup.unlink()
            self.stdout.write(f"Removed old backup: {old_backup.name}")
