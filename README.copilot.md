# AWS Copilot Deployment Guide for Helix Server 2.0

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Environment Setup](#environment-setup)
4. [Service Initialization and Deployment](#service-initialization-and-deployment)
5. [Post-Deployment Setup](#post-deployment-setup)
6. [Additional Configuration](#additional-configuration)
7. [Deactivating the Project/Service](#deactivating-the-projectservice)
8. [Restarting Individual Services](#restarting-individual-services)
9. [Troubleshooting](#troubleshooting)
10. [Future Improvements](#future-improvements)
11. [Stale Dependencies](#stale-dependencies)

## Prerequisites

- AWS CLI installed and configured
- AWS Copilot CLI installed (https://aws.github.io/copilot-cli/)
- Docker installed and running
- A domain registered in AWS Route 53 (for production deployments)

## Initial Setup

1. Setup Copilot on your local device
2. Ensure all service versions are updated to the latest compatible versions (e.g., RDS PostgreSQL, S3 bucket policy)

### If using a new AWS Account:
- Setup a new hosted zone on Route 53
- Update domain references in the copilot/pipeline files to refer to the new domain
- Update S3 bucket names in the file: `copilot/api/addons/helix-s3.yml`

## Environment Setup

1. Initialize the Copilot application:
   ```bash
   copilot app init --domain idmcdb.org
   ```

2. Initialize the environment:
   ```bash
   copilot env init --name staging --default-config
   ```
   Note: If prompted, select the relevant AWS Profile or export using `AWS_PROFILE=<profile-name>`

3. Deploy the environment:
   ```bash
   copilot env deploy --name staging
   ```

## Service Initialization and Deployment

1. Initialize the API service:
   ```bash
   copilot svc init --name api
   ```

2. Initialize the worker service:
   ```bash
   copilot svc init --name worker
   ```

3. Deploy the services (starting with staging environment):
   ```bash
   copilot svc deploy --name api --env staging
   copilot svc deploy --name worker --env staging
   ```

Important Note: If initial deployment fails, delete the S3 buckets and try again.

## Post-Deployment Setup

After successful deployment, follow these steps to set up the Django application:

1. Connect to the ECS container's bash shell:
   ```bash
   copilot svc exec --name api --env <environment-name> -c /bin/bash
   ```
   Note: If prompted for a password, use your device's user password.

2. Once connected, run the init script:
   ```bash
   ./init.sh
   ```
   Note: If you encounter a permission error, make the file executable:
   ```bash
   chmod +x init.sh
   ```

3. If setting up from a local device (not needed for CI builds), run the following commands manually:
   ```bash
   ./manage.py collectstatic
   ./manage.py migrate
   ./manage.py init_roles
   ```

Important: The `aws/session-manager-plugin` is required to use `copilot exec` commands. Ensure it's installed on your local machine.

## Additional Configuration

### Database

- The RDS cluster (Aurora PostgreSQL) is directly linked to the web server.
- Access is shared with the worker using a secret created in the Secrets Manager for the Aurora cluster, achieved using SSM parameter.
- The RDS cluster is added to the security group where Ingress access is provided to the application level environment:
  ```yaml
  SourceSecurityGroupId: { 'Fn::ImportValue': !Sub '${App}-${Env}-EnvironmentSecurityGroup' }
  ```

### S3 Storage

- Public ACLs are enabled in the addon for S3 storage
- The S3 bucket name is defined in the S3 addon YAML file
- To set up S3 buckets with required policies:
  ```bash
  sh deploy/scripts/s3_bucket_setup.sh
  ```

### Redis Elastic Cache

- Access to Redis is passed through secrets for web and worker
- Environment variable access is possible

### Sharing Variables or ARNs

Use CloudFormation Export:
https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html

Example: https://github.com/aws-samples/startup-kit-templates/blob/master/templates/aurora.cfn.yml#L406

## Deactivating the Project/Service

To deactivate or remove the project or specific services, follow these steps:

1. Delete a specific service:
   ```bash
   copilot svc delete --name <service-name> --env <environment-name>
   ```
   Replace `<service-name>` with either `api` or `worker`, and `<environment-name>` with the appropriate environment (e.g., `staging` or `prod`).

2. Delete an entire environment:
   ```bash
   copilot env delete --name <environment-name>
   ```
   This will remove all services and resources associated with the specified environment.

3. Delete the entire application:
   ```bash
   copilot app delete
   ```
   This will remove all environments, services, and resources associated with the application. Use with caution!

Note: Always ensure you have backups of important data before deleting resources.

## Restarting Individual Services

To restart individual services without redeploying the entire application, use the following steps:

1. Restart the API service:
   ```bash
   copilot svc deploy --name api --env <environment-name>
   ```

2. Restart the worker service:
   ```bash
   copilot svc deploy --name worker --env <environment-name>
   ```

Replace `<environment-name>` with the appropriate environment (e.g., `staging` or `prod`).

These commands will redeploy the specified service with the latest configuration and code changes. If you need to force a restart without any changes, you can use the `--force` flag:

```bash
copilot svc deploy --name <service-name> --env <environment-name> --force
```

This can be useful if you need to restart a service due to temporary issues or to apply changes in the underlying infrastructure.

## Troubleshooting

- If a process within a service/task is getting killed, check `dmesg`. It might be running out of memory.
- When deploying an environment for the first time, if the pipeline is unable to create Addon stacks, deploy the environment manually first using `svc deploy -e ENV`. Then add the env to the pipeline and run `pipeline update`.
- Ensure that secrets are used from the same given app and environment when required.
- Make sure names are unique across environments by attaching `${Env}` to the names.
- If the ECS dashboard displays the number of tasks as 0:
   - Set the task count to 1 for both the `api` and `worker` services to initiate container orchestration.

## Future Improvements

1. Update bucket configuration in `helix-s3.yml`:
   - Replace `AccessControl: PublicRead` with:
     ```yaml
     PublicAccessBlockConfiguration:
         BlockPublicAcls: false
         BlockPublicPolicy: false
         IgnorePublicAcls: false
         RestrictPublicBuckets: false
     ```
   Note: `PublicRead` is deprecated by AWS.

2. Update PostgreSQL to a newer version (15+) from 13 to avoid compatibility issues. This would require a complete test for breaking changes.

For more detailed information on Copilot commands, refer to the [official documentation](https://aws.github.io/copilot-cli/docs/getting-started/first-app-tutorial/).

## Stale Dependencies

As of August 2024, the Helix Server uses the following dependencies. Many libraries are several years old, and while not currently critical, it's important to note that the service will eventually need significant updating. To assist future planners, a list of the current deployed versions of each library in the server infrastructure and their corresponding versions as of August 2024 are compiled below. While updates may not always involve bringing a library to the latest version (for instance, Django's long-term support version is currently 4.2), this list illustrates the eventual need for substantial updates.

Software rot significantly impacts custom applications over time. As underlying libraries, frameworks, and system dependencies age, they become less compatible with modern systems, potentially introducing security vulnerabilities and performance issues. Regular updates are crucial for maintaining security, stability, and efficiency, ensuring compatibility with newer technologies and preventing costly overhauls. Neglecting updates may lead to increased technical debt, making the application more difficult and expensive to maintain or enhance.

### Version Comparison Table

This table compares the currently deployed versions of libraries in the Helix Server against their latest available versions as of August 2024. It lists various software dependencies, including frameworks, utilities, and development tools, showcasing the discrepancies between deployed and current versions. This comparison helps identify potential areas for updates in the server's software stack to maintain security, performance, and compatibility

| Library | Deployed Version | Current Version |
|---------|-----------------|-----------------|
| Django | 3.2 | 5.1[2] |
| bleach | 3.3.0 | 6.1.0 |
| boto3 | 1.34.19 | 1.34.34 |
| celery | 5.1.1 | 5.3.6 |
| django-cors-headers | 3.4.0 | 4.3.1 |
| django-debug-toolbar | 2.2 | 4.3.0 |
| django-enumfield | 3.1 | 3.1 |
| django-extensions | 3.0.4 | 3.2.3 |
| django-filter | 2.3.0 | 23.5 |
| django-graphiql-debug-toolbar | 0.1.4 | 0.2.0 |
| django-otp | 1.0.6 | 1.3.0 |
| django-redis | 4.12.1 | 5.4.0 |
| django-rest-framework | 0.1.0 | 0.1.0 |
| django-ses | 2.0.0 | 3.5.2 |
| django-storages | 1.10.1 | 1.14.2 |
| djoser | 2.0.3 | 2.2.2 |
| factory-boy | 3.0.1 | 3.3.0 |
| filemagic | 1.6 | 1.6 |
| graphene-django | 2.13.0 | 3.2.0 |
| graphene-django-extras | 0.4.9 | 1.0.0 |
| graphene-file-upload | 1.2.2 | 1.3.0 |
| graphene-graphiql-explorer | 0.0.1 | 0.1.1 |
| ipython | * | 8.18.1 |
| lxml | 4.6.3 | 5.1.0 |
| mock | 4.0.2 | 5.1.0 |
| openpyxl | 3.0.6 | 3.1.2 |
| pdfkit | 0.6.1 | 1.0.0 |
| psycopg2 | 2.8 | 2.9.9 |
| python | ^3.8 | 3.12.1 |
| requests | * | 2.31.0 |
| selenium | 3.141.0 | 4.16.0 |
| sentry-sdk | >=1,<2 | 1.39.1 |
| shapely | 2.0.1 | 2.0.2 |
| six | 1.15 | 1.16.0 |
| turfpy | 0.0.6 | 0.0.7 |
| uWSGI | * | 2.0.23 |
| django-environ | ^0.8.1 | 0.11.2 |
| drf-spectacular | * | 0.27.0 |
| django-admin-autocomplete-filter | * | 0.7.1 |
| colorlog | * | 6.8.0 |
