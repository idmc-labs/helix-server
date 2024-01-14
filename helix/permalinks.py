from django.conf import settings


class Permalink:
    # TODO: Add test for permalink generation
    # TODO: Remove all current_*

    BASE_URL = f'{settings.FRONTEND_BASE_URL}/permalink'
    CURRENT_URL = f'{settings.FRONTEND_BASE_URL}'

    @classmethod
    def generate_url(cls, url: str, absolute=True):
        _url = url.lstrip('/')
        if not absolute:
            return f'/{_url}'
        return f'{cls.BASE_URL}/{_url}'

    @classmethod
    def figure(cls, entry_id: int, figure_id: int, absolute=True):
        return cls.generate_url(f'/figures/{entry_id}/{figure_id}', absolute=absolute)

    @classmethod
    def current_figure(cls, entry_id: int, figure_id: int, absolute=True):
        return cls.generate_url(f'/entries/{entry_id}/?id={figure_id}#/figures-and-analysis', absolute=absolute)
