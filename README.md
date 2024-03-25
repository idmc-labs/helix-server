# Helix Server

[![Build Status](https://github.com/idmc-labs/helix-server/actions/workflows/test_runner.yml/badge.svg)](https://github.com/idmc-labs/helix-server/actions)
[![Maintainability](https://api.codeclimate.com/v1/badges/2322f4f0041caffe4742/maintainability)](https://codeclimate.com/github/idmc-labs/helix-server/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/2322f4f0041caffe4742/test_coverage)](https://codeclimate.com/github/idmc-labs/helix-server/test_coverage)

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

```bash
python manage.py split_geojson
```

### Generate fresh graphql schema.
```bash
python manage.py graphql_schema --out schema.graphql
```

## Populate pre 2016 conflict and disaster data for GIDD
```bash
python manage.py update_pre_2016_gidd_data.py old_conflict_data.csv old_disaster_data.csv
```
### Populate IDPs SADD estimates table
```bash
python manage.py update_idps_sadd_estimates idps_sadd_estimates.csv
```

### Setup S3 buckets

This will create appropriate buckets with required policies based on the `.env`.

```bash
sh deploy/scripts/s3_bucket_setup.sh
```

### To enable two factor authentication (generate statictoken) of admin user from command line
```bash
python manage.py addstatictoken -t 123456 "admin@idmcdb.org"
```

## Management Command
There are custom management commands available to facilitate specific tasks.

### Populate figure `Calculation Logic`
```bash
./manage.py populate_calculation_logic_field
```
> NOTE: This command populates the `calculation_logic` field in the Figure Table if there is no existing data in it.

