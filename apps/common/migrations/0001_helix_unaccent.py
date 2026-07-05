from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations

# unaccent() is only STABLE (its output depends on the unaccent dictionary), so
# index expressions can't use it directly. helix_unaccent_dict exposes the
# extension's C entry point with the dictionary pinned explicitly and declares
# IMMUTABLE: the contract is that the public.unaccent dictionary never changes
# (if it ever does, REINDEX the trigram indexes). The one-arg helix_unaccent
# wrapper is deliberately NOT STRICT so the planner can inline it -- calls
# collapse to the C function (no per-row SQL-function overhead) and index
# expressions still match because both sides inline identically.
# DEPLOY: CREATE EXTENSION and LANGUAGE c functions need superuser.
# Everything in the wrapper body is schema-qualified: CREATE INDEX compiles its
# expression as a security-restricted operation (search_path = pg_catalog), and
# the body is re-parsed there when the planner inlines the wrapper.
CREATE_FUNCTIONS = r"""
CREATE OR REPLACE FUNCTION public.helix_unaccent_dict(regdictionary, text) RETURNS text
  LANGUAGE c IMMUTABLE PARALLEL SAFE STRICT
  AS '$libdir/unaccent', 'unaccent_dict';
CREATE OR REPLACE FUNCTION public.helix_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE
  AS $$ SELECT public.helix_unaccent_dict('public.unaccent'::regdictionary, $1) $$;
"""
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
