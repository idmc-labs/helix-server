import requests
from django.core.management.base import BaseCommand
from apps.entry.models import Figure


class Command(BaseCommand):
    help = 'Migrate sources and reliability.'

    def handle(self, *args, **options):
        sources_and_reliability = requests.get(
            "https://helix-copilot-staging-helix-media.s3.amazonaws.com/media/sources_and_reliability.json"
        ).json()
        source_and_reliability_map = {item["id"]: item['sources_and_reliability'] for item in sources_and_reliability}
        figures = Figure.objects.filter(old_id__in=source_and_reliability_map.keys())
        for figure in figures:
            source_and_reliability = source_and_reliability_map.get(int(figure.old_id))
            if source_and_reliability:
                figure.calculation_logic = f'''
                {figure.calculation_logic} \n\n###Source and reliability \n {source_and_reliability}
                '''
        Figure.objects.bulk_update(figures, ['calculation_logic', ])
        print(f'{figures.count()} Figures updated')
