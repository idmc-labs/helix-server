# Helix Server

```bash
docker-compose up
```

## Run Migrations
```bash
docker-compose exec server python manage.py migrate 
```

## Initialize DB (optional)
```bash
docker-compose exec server python manage.py loaddata fixtures/users.json
...
```

And navigate to `localhost:9000/graphiql` to view available graphs.

Use `localhost:9000/graphql` to interact with the server from the client.

