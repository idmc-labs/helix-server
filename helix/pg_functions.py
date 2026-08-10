"""Custom PostgreSQL function wrappers.

The DB-side functions are created by `apps/common/migrations/0001_helix_unaccent`
(frozen SQL: a migration importing a mutable constant would let already-migrated
databases silently diverge from fresh ones). Lookups are registered from
`apps.common.apps.CommonConfig.ready`.
"""

from django.db.models import CharField, TextField, Transform


class HelixUnaccent(Transform):
    """The built-in `unaccent` is only STABLE, so no index can serve it.
    helix_unaccent() is an IMMUTABLE plpgsql wrapper over the extension's C
    function with the dictionary pinned (same folding, identical results): the
    trigram indexes serve it where the predicate shape allows, and everywhere
    else it costs about what the bare C call costs -- so it is safe to use for
    every lookup. It is deliberately NOT inlinable; both the query and the index
    expression keep the `helix_unaccent(<col>)` shape and therefore always match."""

    # One-sided folding silently returns 0 rows for accented search terms.
    bilateral = True

    lookup_name = "helix_unaccent"
    function = "HELIX_UNACCENT"


def register_lookups():
    CharField.register_lookup(HelixUnaccent)
    TextField.register_lookup(HelixUnaccent)
