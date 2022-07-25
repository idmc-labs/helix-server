```bash

# Create new app
copilot app init helix-copilot --domain idmcdb.org

# Create new environments
copilot env init --name staging --default-config --profile idmc-copilot
copilot env init --name prod --default-config --profile idmc-copilot

# Push required secrets to AWS.
copilot secret init --cli-input-yaml secrets.yml

copilot svc deploy --name api --env staging
copilot svc deploy --name worker --env staging
```
