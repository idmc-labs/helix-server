### Serverless

#### AWS Profile for deployment

Create a new profile (eg helixProfile) in ~/.aws/credentials directory to be able to deploy the serverless,
based on the credentials in the AWS console. Also to test lambda function locally.

For docker, fill `.env` file with following keys

- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION
- AWS_REGION

#### Serverless plugins

`package.json` provides the required packages

```bash
npm install
```

1. Python Requirements

If and only if package.json is missing. Or you want to ignore package.json

```bash
sls install -n serverless-python-requirements
```

Check this out to install [Serverless](https://www.serverless.com/framework/docs/providers/aws/guide/installation/).

##### Binary for wkhtmltopdf

Is added as a lambda layer

#### The `config.yml`

Serverless deployment variables are stored in `config.yml`.

```yml
S3_BUCKET_NAME: 'togglecorp-helix'
AWS_PROFILE: 'helixProfile'
```

#### Async Invocation

```bash
aws lambda invoke --profile helixProfile --function-name htmltopdf-dev-generatePdf --invocation-type Event --cli-binary-format raw-in-base64-out --payload '{"url": "https://github.com", "token": "1234123412341234"}' response.json
```

Check this out to install [AWS CLI 2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html) in your linux system.

#### Webhook as success/failure handler

...

Notes
-

- Individual packaging does not work with layers from serverless configuration

