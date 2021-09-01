### General

https://aws.github.io/copilot-cli/

https://aws.github.io/copilot-cli/docs/getting-started/first-app-tutorial/

https://aws.github.io/copilot-cli/docs/developing/additional-aws-resources/

Make sure that you have a domain registered in the route 53

```bash
> copilot app init --domain idmcdb.org
> copilot init
```

Web, worker and cache are currently setup as independent services

Database

- is directly liked with the web server
- however for worker, the web db cluster has exported a SSM resource
    - which is passed as a environment variable (or secret) to the worker
      service
    - IAM policy has been added for the worker service to read the secret
      stored in the ARN (specified inside the SSM)

So, web server has direct access to the `json` auth of the database config.
While worker (or any other service) will only have access to the ARN.
Therefore, the need of IAM policy to read the `secret`.

Regarding the storage, we are using aurora postgres rds cluster which is
directly linked to the web server.
However the access is shared to the worker using simply the secret created in
the secrets manager for aurora cluster, this is achieved using SSM parameter.

The RDS cluster is now added to the security group where Ingress access is
provided to the application level environment:
> SourceSecurityGroupId: { 'Fn::ImportValue': !Sub '${App}-${Env}-EnvironmentSecurityGroup' }

Mind the addon for worker server, we have created iam policy to attach to the
copilot task role, so that the task can read the secret content.

Regarding S3...

- public acl are enabled in the addon for s3 storage

Providing IAM policy of worker with the help of resource tag as explained here:
https://github.com/aws/copilot-cli/issues/1368#issuecomment-689228396 did not
seem to work. It kept raising 403 on trying to save to s3.
This was solved by actually writing down the s3 bucket name as defined in the s3 addon yml

If a process you are trying to run within a service/task is getting killed,
look into `dmesg`, in one of the case it was running out of memory.

- The resources name for s3 bucket access is passed using `export` in the s3
  addon yaml, while it is being used elsewhere. This can be used elsewhere, if
  you need to pass some variable that can be `Fn::Import`ed elsewhere.

Redis Elastic Cache

Access to redis is passed through secrets for web and worker, environment
variable is possible for this though

> See addons/redis-cache.yml and addons/iam-and-env-vars.yml
> The two ways of accessing a variable like `ElastiCacheAddress` in the service it is directly attached to and the other

Sharing a variable or ARN...

We can use `Cloudformation Export` to do that.
https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html
Example: https://github.com/aws-samples/startup-kit-templates/blob/master/templates/aurora.cfn.yml#L406

### Secrets

Make sure that you are actually using the secret (if required) created under
the same given app and environment.

### Pipeline

> Deploying an environment(eg: alpha) for the first time?

Pipeline was unable to create Addon stacks. "Deploy the environment manually
first using `svc deploy -e ENV`". And add the env into the pipeline afterwards
and run `pipeline update`. This might be wrong however.

Lets not try to access the same secret in `test` env from `alpha` env deployment.

NOTE: Make sure the name is unique across environments with `${Env}` attached
to the names.

### Loading data to Serverless RDS

We cannot directly interact with serverless RDS itself.

So, create an EC2 instance which is in the same VPC as the RDS cluster. And
perform db operations in the instance, or even tunnel to the instance to access
the RDS. (Second approach is better)
