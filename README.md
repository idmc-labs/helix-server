# Helix Server

```bash
docker-compose up
```

## Initialize DB (optional)
```bash
docker-compose exec server python manage.py loaddata fixtures/*.json
docker-compose exec server python manage.py create_dummy_users
...
```

And navigate to `localhost:9000/graphiql` to view available graphs.

Use `localhost:9000/graphql` to interact with the server from the client.

