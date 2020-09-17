### Serverless

#### AWS Profile for deployment

Create a new profile (eg helixProfile) in ~/.aws/credentials directory to be able to deploy the serverless,
based on the credentials in the AWS console.

#### Python packaging

`package.json` provides the required packages

```bash
npm install
```

If and only if package.json is missing. Or you want to ignore package.json

```bash
sls install -n serverless-python-requirements
```

##### Binary for wkhtmltopdf

Download from [here](https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.4/wkhtmltox-0.12.4_linux-generic-amd64.tar.xz).
Mind the version. [Latter versions are host dependent](https://medium.com/@_rich/richard-keller-61d9cb0f430).

```bash
pwd
$ <PROJECT_DIR>/serverless/
mkdir ./binary
cd binary
tar -xf wkhtmltox-0.12.4_linux-generic-amd64.tar.xz
```

#### The `config.yml`

Deployment variables are stored in `config.yml`

Notes
-

1. Async Invocation
    
2. Individual packaging does not work with layers from serverless configuration
