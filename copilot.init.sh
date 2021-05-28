#! /bin/bash
# Run migrations
python manage.py migrate

# collect static
python manage.py collectstatic

# Init roles
python manage.py remove_stale_contenttypes
python manage.py init_roles

# Init assets
python manage.py init_types_subtypes # event related
python manage.py init_figure_types # figure related
python manage.py init_figure_tags