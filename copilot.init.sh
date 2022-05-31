#! /bin/bash -xe

# Run migrations
python manage.py migrate

# collect static
python manage.py collectstatic

# Init roles
python manage.py remove_stale_contenttypes
python manage.py init_roles

# Init assets
python manage.py init_types_subtypes # event related
python manage.py init_figure_tags
python manage.py init_osv_sub_type
python manage.py init_other_sub_types
