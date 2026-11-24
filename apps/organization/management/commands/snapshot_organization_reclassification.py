from apps.contrib.management.base.snapshot import BaseSnapshotCommand
from apps.organization.reclassification_snapshot import take_before_snapshot, take_snapshot


class Command(BaseSnapshotCommand):
    help = (
        "Snapshot of the organization reclassification: each organization's kind and each figure's classification "
        "and IDU source wording, written to <output-dir>/organizations.csv and <output-dir>/figures.csv. "
        "Run with --before before the organization migrations (0013, 0014), and without it after."
    )
    label = "organization reclassification"
    before_help = "The database is not migrated yet: read the kind's old reliability with raw SQL."

    # NOTE: --before only works before migrate. Organization 0014 drops the kind's reliability column,
    # which the before snapshot reads, so on a migrated database it stops with an error. The other way
    # round, the after snapshot refuses a database that is not migrated (old kinds have no source type).

    def take(self, output_dir, before):
        counts = (take_before_snapshot if before else take_snapshot)(output_dir, log=self.log)
        return f"{counts['organizations']} organizations and {counts['figures']} figures in {output_dir}"
