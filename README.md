# Helix Server

## Initialize environment

Create a `.env` file in the project folder. (For development, blank file is fine)

## Get started with:

```bash
docker-compose up
```

## Initialize database

```bash
./init.sh
```
## Initialize database (seed)
```bash
# Fix the full_name constraint
docker-compose exec server python manage.py save_users_dummy

docker-compose exec server python manage.py create_dummy_users
docker-compose exec server python manage.py loadtestdata <case sensitive model_names> --count 2
# eg.
# docker-compose exec server python manage.py loadtestdata Country --count 2
# docker-compose exec server python manage.py loadtestdata Resource ResourceGroup --count 2
```

And navigate to `localhost:9000/graphiql` to view available graphs.
Use `localhost:9000/graphql` to interact with the server from the client.
