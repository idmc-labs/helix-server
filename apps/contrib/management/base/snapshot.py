"""The reusable before/after snapshot management command base class."""

import os

from django.core.management.base import BaseCommand


def no_log(kind: str, message: str) -> None:
    """The default log of the snapshot functions when no command prints their progress."""


class BaseSnapshotCommand(BaseCommand):
    """
    Writes a snapshot to a directory, once before a migration (--before) and once after,
    to compare by hand.

    Subclasses set ``label`` and ``before_help``, and implement ``take``, which writes the files
    and returns a one-line summary. ``take`` reports its progress through ``log``.
    """

    #: What is snapshotted, e.g. "organization reclassification".
    label = ""
    #: What --before changes, shown in --help.
    before_help = "The database is not migrated yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir", required=True, help="Directory to write the snapshot to; created if it does not exist."
        )
        parser.add_argument("--before", action="store_true", help=self.before_help)

    def log(self, kind: str, message: str) -> None:
        """kind: "step" (a new step starts), "progress" (rows written so far) or "done" (a file is written)."""
        if kind == "step":
            self.stdout.write(self.style.NOTICE(f"\n--- {message}"))
        elif kind == "progress":
            self.stdout.write(f"\t... {message}")
        else:
            self.stdout.write(self.style.SUCCESS(f"\t--> {message}"))

    def take(self, output_dir: str, before: bool) -> str:
        raise NotImplementedError

    def handle(self, *args, **options):
        output_dir: str = options["output_dir"]
        before: bool = options["before"]
        when = "BEFORE" if before else "AFTER"
        self.stdout.write(self.style.NOTICE(f"--- Taking the {when} migration {self.label} snapshot into {output_dir}"))
        os.makedirs(output_dir, exist_ok=True)
        summary = self.take(output_dir, before)
        self.stdout.write(self.style.SUCCESS(f"\n{when} {self.label} snapshot done: {summary}\n"))
