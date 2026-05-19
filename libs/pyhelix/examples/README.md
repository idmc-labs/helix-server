## Usages

Setup helix credentials, Create **libs/pyhelix/examples/.env**
```dotenv
# HELIX_BASE_DOMAIN="https://helix-tools-api-staging.idmcdb.org"
HELIX_EMAIL="your@email.com"
HELIX_PASSWORD="super-secret-password"
```

```bash
# Run the example script
uv run run.py

# View the generated files
fx generated/helix-import.jsonl
```
> [!NOTE]
> uv -> https://github.com/astral-sh/uv
>
> fx -> https://github.com/antonmedv/fx

## Troubleshooting

### Using local running helix-server

Make sure to include this in your `.env` file
```dotenv
SESSION_COOKIE_DOMAIN=""
CSRF_COOKIE_DOMAIN=""
```
> [!NOTE]
> [httpx](https://github.com/projectdiscovery/httpx) doesn't store cookie for `Domain=localhost` when used by **set-cookie**
