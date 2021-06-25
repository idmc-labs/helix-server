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

copilot init

make sure that you have a domain registered in the route 53
```bash
example
copilot app init --domain idmcdb.org
```

Django, dramatiq and redis are currently setup as independent services

Database

- is directly liked with the django server
- however for dramatiq, the djnago db cluster has exported a SSM resource
    - which is passed as a environment variable (or secret) to the dramatiq service
    - IAM policy has been added for the dramatiq service to read the secret stored in the ARN (specified inside the SSM)

~Regarding the storage, we are using aurora postgres rds cluster which is directly linked to the django server.~
~However the access is shared to the dramatiq using simply the secret created in the secrets manager for aurora cluster, this is achieved using SSM parameter.~

The RDS cluster is now added to the security group where Ingree access is provided to the application level environment:
> SourceSecurityGroupId: { 'Fn::ImportValue': !Sub '${App}-${Env}-EnvironmentSecurityGroup' }

Mind the addon for dramatiq server, we have created iam policy to attach to the copilot task role, so that the task can read the secret content.

We will be doing the same for rds access.

Regarding S3...

- public acl are enabled in the addon for s3 storage

Providing IAM policy of dramatiq with the help of resource tag as explained here: https://github.com/aws/copilot-cli/issues/1368#issuecomment-689228396 did not seem to work. It kept raising 403 on trying to save to s3.
This was solved by actually writing down the s3 bucket name as defined in the s3 addon yml

If a process you are trying to run within a service/task is getting killed, look into `dmesg`, in one of the case it was running out of memory.

Redis Elastic Cache

Access to redis is passed through secrets for django and dramatiq, environment variable is possible for this though

> Sharing a variable or ARN

We can use `Cloudformation Export` to do that. 
https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html
Example: https://github.com/aws-samples/startup-kit-templates/blob/master/templates/aurora.cfn.yml#L406

### Secrets

Make sure that you are actually using the secret (if required) created under the same given app and environment.

### Pipeline

> Deploying an environment(eg: prod) for the first time?

Pipeline was unable to create Addon stacks. "Deploy the environment manually first using `svc deploy -e ENV`". And add the env into the pipeline afterwards and run `pipeline update`.

Lets not try to access a secret in `test` env from `prod` env deployment.

Make sure the name is unique across environments
