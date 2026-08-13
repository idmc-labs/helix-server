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
    function with the dictionary pinned (same folding, identical results), so the
    trigram indexes serve it where the predicate shape allows. Where they cannot,
    every row pays a plpgsql invocation around the C call: 1.2-1.7x the bare call
    on CPU-bound shapes, and the wrapper's ASCII short-circuit is itself a net
    loss on accented-heavy input. That cost buys deployability -- making the
    wrapper inlinable needs ownership of the extension's STABLE function or a
    LANGUAGE c function of our own, and both are superuser-only, which
    `rds_superuser` on Aurora/RDS is not. Being NOT inlinable is also what keeps
    the query and the index expression at the same `helix_unaccent(<col>)` shape,
    so they always match."""

    # One-sided folding silently returns 0 rows for accented search terms.
    bilateral = True

    lookup_name = "helix_unaccent"
    function = "HELIX_UNACCENT"


def register_lookups():
    CharField.register_lookup(HelixUnaccent)
    TextField.register_lookup(HelixUnaccent)
