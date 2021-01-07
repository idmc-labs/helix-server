# Helix Server

```bash
docker-compose up
```

## Run Migrations
```bash
docker-compose exec server python manage.py migrate
```

## Initialize Roles
```bash
docker-compose exec server python manage.py init_roles
```

## Initialize assets
```bash
docker-compose exec server python manage.py init_countries
docker-compose exec server python manage.py init_organizations
docker-compose exec server python manage.py init_types_subtypes
docker-compose exec server python manage.py init_communication_media
```

## Initialize DB (optional)
```bash
docker-compose exec server python manage.py create_dummy_users
docker-compose exec server python manage.py loadtestdata <case sensitive model_names> --count 2
# eg.
# docker-compose exec server python manage.py loadtestdata Country --count 2
# docker-compose exec server python manage.py loadtestdata Resource ResourceGroup --count 2
```

And navigate to `localhost:9000/graphiql` to view available graphs.

Use `localhost:9000/graphql` to interact with the server from the client.

