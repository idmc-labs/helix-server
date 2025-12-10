import logging

from django.core.management.base import BaseCommand

from apps.contrib.tasks import (
    generate_idus_all_disaster_dump_file,
    generate_idus_all_disaster_dump_file_source_less,
    generate_idus_all_dump_file,
    generate_idus_all_dump_file_source_less,
    generate_idus_dump_file,
    generate_idus_dump_file_source_less,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate IDUS dump files"

    def handle(self, *args, **options):
        try:
            generate_idus_dump_file()
            generate_idus_all_dump_file()
            generate_idus_all_disaster_dump_file()
            logger.info("IDUS dump files generated successfully")

            # generate idu data without source
            generate_idus_dump_file_source_less()
            generate_idus_all_dump_file_source_less()
            generate_idus_all_disaster_dump_file_source_less()
            logger.info("IDUS dump files without source generated successfully")

        except Exception:
            logger.error("Error generating IDUS dump files:", exc_info=True)
