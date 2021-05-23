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

## One time commands

### Save geojson for each country

docker-compose exec server python manage.py split_geojson

## Setup S3 buckets

This will create appropriate buckets with required policies based on the `.env`.

```bash
sh deploy/scripts/s3_bucket_setup.sh
```

## AWS Copilot

https://aws.github.io/copilot-cli/

https://aws.github.io/copilot-cli/docs/getting-started/first-app-tutorial/

https://aws.github.io/copilot-cli/docs/developing/additional-aws-resources/

Django, dramatiq and redis are currently setup as independent services

Access to redis is passed through secrets for django and dramatiq, environment variable is possible for this though

~Regarding the storage, we are using aurora postgres rds cluster which is directly linked to the django server.~
~However the access is shared to the dramatiq using simply the secret created in the secrets manager for aurora cluster, this is achieved using SSM parameter.~

The rds cluster is now added to the security group where Ingree access is provided to the application level environment:
> SourceSecurityGroupId: { 'Fn::ImportValue': !Sub '${App}-${Env}-EnvironmentSecurityGroup' }

Mind the addon for dramatiq server, we have created iam policy to attach to the copilot task role, so that the task can read the secret content.

We will be doing the same for rds access.

Regarding S3...
