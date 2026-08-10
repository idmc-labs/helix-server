from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations

# unaccent() is only STABLE (its output depends on the unaccent dictionary), so index
# expressions can't use it directly. helix_unaccent pins the dictionary explicitly and
# declares IMMUTABLE: the contract is that the public.unaccent dictionary never changes
# (if it ever does, REINDEX the trigram indexes). The body is fully schema-qualified because
# CREATE INDEX compiles its expression as a security-restricted operation
# (search_path = pg_catalog).
#
# This `LANGUAGE sql` body does NOT inline: the planner refuses to inline an IMMUTABLE SQL
# function whose body calls a STABLE one, and `public.unaccent(regdictionary, text)` is STABLE,
# so every row pays a full SQL-function invocation. 0002_helix_unaccent_plpgsql replaces the
# body with the plpgsql equivalent, which is what actually runs; this file is left verbatim
# because a migration's SQL is frozen. Read 0002 for the current definition and the reasoning.
#
# DEPLOY: this needs CREATE EXTENSION but NOT superuser. It deliberately calls the two-arg
# `public.unaccent(regdictionary, text)` that the extension itself installs, rather than
# declaring our own LANGUAGE c function bound to $libdir/unaccent -- that would be an exact
# duplicate of the extension's entry point AND would require a true superuser, which
# `rds_superuser` on Aurora/RDS is not, failing the deploy and blocking every index
# migration behind it.
CREATE_FUNCTIONS = r"""
CREATE OR REPLACE FUNCTION public.helix_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE
  AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;
"""
# Drop the legacy C duplicate too: environments that ran the earlier version of this
# migration still carry it, and nothing references it once the wrapper above is replaced.
DROP_FUNCTIONS = (
    "DROP FUNCTION IF EXISTS helix_unaccent(text);DROP FUNCTION IF EXISTS helix_unaccent_dict(regdictionary, text);"
)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        # This migration has no dependencies, so it cannot rely on the older
        # migration that first created the unaccent extension having run.
        UnaccentExtension(),
        TrigramExtension(),
        migrations.RunSQL(CREATE_FUNCTIONS, DROP_FUNCTIONS),
    ]
