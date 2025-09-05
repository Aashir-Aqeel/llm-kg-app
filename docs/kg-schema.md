# Knowledge Graph Schema

## Node labels
- `Person` — properties: `id` (unique), `name`
- `Place`  — properties: `id`, `name`
- `Org`    — properties: `id`, `name`
- `Goal`   — properties: `id`, `name`

## Relationships
- `LIVES_IN(Person→Place)`
- `WORKS_AT(Person→Org)`
- `SIBLING_OF(Person↔Person)` (undirected semantics stored as two directed edges if needed)
- `FRIEND_OF(Person↔Person)`
- `HAS_GOAL(Person→Goal)`
- `MET_WITH(Person→Person)`

All relationships may carry:
- `text` (short source snippet),
- `confidence` (0..1),
- `created_at` (ISO 8601),
- `source_id` (message id).

## Constraints
- Uniqueness on `(:Person {id})`, `(:Place {id})`, `(:Org {id})`, `(:Goal {id})`.

## Invariants
- Never write blank ids.
- Labels/rel types must match the enums above (enforced by Pydantic).
