#! /bin/bash -xe
# Run migrations
docker-compose exec server python manage.py migrate

# Init roles
docker-compose exec server python manage.py remove_stale_contenttypes
docker-compose exec server python manage.py init_roles

# Init assets
docker-compose exec server python manage.py init_types_subtypes # event related
docker-compose exec server python manage.py init_figure_types # figure related
docker-compose exec server python manage.py init_figure_tags
docker-compose exec server python manage.py init_osv_sub_type
