import os

from apps.contrib.management.base.snapshot import BaseSnapshotCommand
from apps.gidd.publish_check import SNAPSHOT_FILE, take_snapshot


class Command(BaseSnapshotCommand):
    help = (
        "Write the published columns of every GIDD figure to <output-dir>/gidd_figures.csv. "
        "Run right after a publish: with --before before the migrations, and without it after."
    )
    label = "GIDD"
    before_help = "The database is not migrated yet (gidd 0047): leave out the new sources_sub_type column."

    # NOTE: --before only works before migrate. gidd 0047 adds the sources_sub_type column; the before
    # snapshot leaves it out, so on a migrated database it stops with an error rather than write a
    # snapshot that misses the new column. The after snapshot needs the column, so it refuses a
    # database that is not migrated.

    def take(self, output_dir, before):
        path = os.path.join(output_dir, SNAPSHOT_FILE)
        count = take_snapshot(path, before=before, log=self.log)
        return f"{count} GIDD figures in {path}"
