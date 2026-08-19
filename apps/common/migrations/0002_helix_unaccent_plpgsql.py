from django.db import migrations

# WHY: 0001 declared `helix_unaccent` as `LANGUAGE sql` on the premise that the planner would
# inline it into the extension's C call. It does not. Inlining requires everything the body
# calls to be IMMUTABLE, and `public.unaccent(regdictionary, text)` is STABLE, so every row
# paid a full SQL-function invocation on the paths no index can serve (seq scans, index
# rechecks, cross-table ORs).
#
# plpgsql runs a single-expression body through the simple-expression path, which is
# substantially cheaper than the SQL-function machinery, and the ASCII short-circuit skips the
# call entirely for the values that have nothing to fold.
#
# WHY NOT `ALTER FUNCTION public.unaccent(regdictionary, text) IMMUTABLE` (the usual advice,
# which would make the sql wrapper inline): it needs ownership of that function, and unaccent
# is a *trusted* extension, so PostgreSQL creates its objects as the bootstrap superuser no
# matter which role runs CREATE EXTENSION. On Aurora/RDS that owner is `rdsadmin`, which no
# customer role -- including the master user and every `rds_superuser` member -- can assume.
# Declaring our own `LANGUAGE c` function is likewise superuser-only. So the wrapper cannot be
# made inlinable on Aurora, and it is better that it never depends on inlining: if it did, a
# later change in inlining state (an extension upgrade resetting the volatility, a DBA applying
# the ALTER) would silently stop the query expression from matching the stored index expression.
#
# NO REINDEX IS REQUIRED. CREATE OR REPLACE keeps the function's OID, so the trigram indexes
# built on UPPER(helix_unaccent(<col>)::text) keep matching the query expression, and the
# values they store are unchanged -- the new body calls the same C entry point with the same
# dictionary.
#
# The ASCII short-circuit is exact: no rule in unaccent.rules has an ASCII character in its
# source, so unaccent is the identity on pure-ASCII input.
# `octet_length = length` only identifies pure-ASCII input in a multibyte server encoding --
# in a single-byte one it holds for every string and the short-circuit would silently disable
# accent folding -- so it is installed only when the database encoding is multibyte, and the
# plain wrapper is installed otherwise. Both bodies are fully schema-qualified: a plpgsql body
# is parsed lazily under whatever search_path is current when it first runs, and the
# maintenance operations that evaluate index expressions restrict it to pg_catalog.
CREATE_FUNCTIONS = r"""
DO $do$
BEGIN
  IF (SELECT pg_encoding_max_length(encoding) FROM pg_database WHERE datname = current_database()) > 1 THEN
    EXECUTE $ddl$
      CREATE OR REPLACE FUNCTION public.helix_unaccent(text) RETURNS text
        LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE
        AS $fn$
          BEGIN
            IF octet_length($1) = length($1) THEN
              RETURN $1;
            END IF;
            RETURN public.unaccent('public.unaccent'::regdictionary, $1);
          END
        $fn$
    $ddl$;
  ELSE
    EXECUTE $ddl$
      CREATE OR REPLACE FUNCTION public.helix_unaccent(text) RETURNS text
        LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE
        AS $fn$
          BEGIN
            RETURN public.unaccent('public.unaccent'::regdictionary, $1);
          END
        $fn$
    $ddl$;
  END IF;
END
$do$;
"""
# Reverse: the `LANGUAGE sql` wrapper 0001 installs. Same results, slower per row.
RESTORE_SQL_FUNCTIONS = r"""
CREATE OR REPLACE FUNCTION public.helix_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE
  AS $fn$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $fn$;
"""


class Migration(migrations.Migration):
    dependencies = [("common", "0001_helix_unaccent")]

    operations = [migrations.RunSQL(CREATE_FUNCTIONS, RESTORE_SQL_FUNCTIONS)]
