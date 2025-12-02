
## Adding new permission

### Add permission to the model

> [!NOTE]
> This document uses **sign_off_report** as an example. It already exists in the codebase.

```python
class Report:
    ...
    class Meta:
        permissions = (
            ("sign_off_report", "Can sign off the report"),
            ...
        )
```

> [!IMPORTANT]
> The permission key must follow this format: **`<action>_<model-name>`**

### Create Django migration

```bash
./manage.py makemigrations
./manage.py migrate
```

### Update permission mapping

#### Update permission values in **apps/users/enums.py**

**PERMISSION_ACTION**

```python
class PERMISSION_ACTION(enum.Enum):
    ...
    sign_off = 3

    __labels__ = {
        ...
        sign_off: _("Sign Off"),
    }
```
> [!NOTE]
> This defines the action part of the permission.

> [!IMPORTANT]
> Make sure to use the `action` part from the permission **`<action>_<model-name>`** defined in the models

**PERMISSION_ENTITY**

```python
class PERMISSION_ENTITY(enum.Enum):
    ...
    report = 17

    __labels__ = {
        ...
        report: _("Report"),
    }
```
> [!NOTE]
> This defines the model related to the permission.

> [!IMPORTANT]
> Make sure to use the `model-name` part from the permission **`<action>_<model-name>`** defined in the models


#### Update role permissions in **apps/users/roles.py**

**PERMISSIONS**

```python
PERMISSIONS = {
    USER_ROLE.ADMIN: {
        ...
        PERMISSION_ACTION.sign_off: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.event},
    },
    USER_ROLE.DIRECTORS_OFFICE: {
        ...
        PERMISSION_ACTION.sign_off: set(),
    },
    ...
}
```

> [!CAUTION]
> Every role must include the action. Use **set()** if the role should not have this permission.

### Using the permission

Now you can use the new permission in a mutation:

```python
from utils.permissions import permission_checker

class GenerateReport(graphene.Mutation):
    ...

    @permission_checker(["report.sign_off_report"])
    def mutate(root, info, id):
        ...
```

#### Run init role command to sync the permission mapping with database

```bash
docker compose exec server python manage.py init_roles
```

## Adding new Role

TODO

