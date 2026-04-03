# Emerging Event (Isolated from Main Event)

This project now supports an isolated Emerging event flow without affecting Main event pages or logic.

## What is isolated

- Main routes stay unchanged:
  - `/tournament/live`
  - `/tournament/results`
- Emerging routes are separate:
  - `/emerging/live`
  - `/emerging/results`
- Emerging rounds use unique names and orders:
  - `Emerging Quarter` (order `101`)
  - `Emerging Semi Final` (order `102`)
  - `Emerging Final` (order `103`)

## Rules implemented

1. Qualification source: **Group Stage locked scores**.
2. Selection: **bottom 8 teams by lowest point difference (PF-PA)**.
3. Emerging Quarter pairings:
   - `1 vs 8`
   - `2 vs 7`
   - `3 vs 6`
   - `4 vs 5`
4. Emerging Semi pairings:
   - winner of `(1 vs 8)` vs winner of `(4 vs 5)`
   - winner of `(2 vs 7)` vs winner of `(3 vs 6)`
5. Emerging Final:
   - winner of semi 1 vs winner of semi 2

## Match settings

Emerging rounds are configured with:
- `points_per_set = 15`
- `sets_per_match = 1` (can be changed in DB/admin if needed)

## How to run

Generate Emerging Quarter (initial bracket):

```bash
python manage.py generate_emerging
```

Regenerate from scratch (deletes existing Emerging matches first):

```bash
python manage.py generate_emerging --force
```

Advance rounds after winners are locked:

```bash
python manage.py advance_emerging
```

Run `advance_emerging` again after Emerging Semi is complete to generate Emerging Final.
