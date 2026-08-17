# New GIDD Tables: GiddDisaggregatedDisplacement & GiddEventDisplacement

## Overview

Two new tables that extend GIDD with subtype-level granularity for both conflict and disaster displacement. They replace the role of `gidd_conflict` + `gidd_disaster` + `gidd_displacementdata` for new use cases but do **not** remove those tables.

---

## GiddDisaggregatedDisplacement (`gidd_gidddisagggregateddisplacement`)

Displacement figures aggregated by **country + year + cause + subtype**.

Each row represents the total displacement for a specific country, year, crisis cause, and violence/hazard subtype combination.

### Grouping Keys

| Cause | Group By |
|---|---|
| Conflict | `country + year + violence + violence_sub_type` |
| Disaster | `country + year + hazard_type + hazard_sub_type` |

`violence_sub_type` can be null (figures with violence type but no subtype are included, not excluded).

### Fields

```
country             FK → Country
iso3                cached
country_name        cached
year
cause               conflict | disaster

# Conflict (null for disaster rows)
violence            FK → Violence
violence_name       cached
violence_sub_type   FK → ViolenceSubType (nullable)
violence_sub_type_name cached

# Disaster (null for conflict rows)
hazard_category         FK → DisasterCategory (cached name)
hazard_sub_category     FK → DisasterSubCategory (cached name)
hazard_type             FK → DisasterType (cached name)
hazard_sub_type         FK → DisasterSubType (cached name)

# Figures
new_displacement            BigInt (nullable)
new_displacement_rounded    BigInt (nullable)
total_displacement          BigInt (nullable)
total_displacement_rounded  BigInt (nullable)
```

---

## GiddEventDisplacement (`gidd_giddeventdisplacement`)

Same as `GiddDisaggregatedDisplacement` but disaggregated further by **event**. One row per event + country + year + cause + subtype.

Unified table for both conflict and disaster events — replaces the role of `gidd_disaster` for new consumers, and fills the gap for conflict (which had no event-level table).

### Additional Fields (on top of GiddDisaggregatedDisplacement)

```
event           FK → Event (SET_NULL, nullable)
event_raw_id    IntegerField (nullable) — preserved when event FK is nulled
event_name      cached
start_date, start_date_accuracy
end_date, end_date_accuracy
event_codes         ArrayField
event_codes_type    ArrayField
```

---

## Data Source & Population

- **Source:** Helix `Figure` records with `role=RECOMMENDED`, post-2016 only.
- **No legacy data** — `ConflictLegacy` and `DisasterLegacy` are not used.
- **Rebuild strategy:** Full delete + bulk_create on every `update_gidd_data` run, inside the same `transaction.atomic()` block as all other GIDD tables.

---

## Pending

- [ ] GraphQL queries (`gidd_public_*`) for both tables — to be added separately
- [ ] REST dump endpoints and existing GIDD stats/listing endpoints to be routed to these tables — to be handled separately
