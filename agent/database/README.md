# Database (SQLAlchemy ORM)

Schema and seed data live in Python under `clinic/orm/`:

- `clinic/orm/tables.py` — SQLAlchemy models (replaces `001_schema.sql`)
- `clinic/orm/seed.py` — demo seed data (replaces `002_seed.sql`)

Initialize tables and seed from the **agent** folder:

```bash
cd agent
.venv/bin/pip install -e .
.venv/bin/python scripts/init_db.py
```

This creates all tables via `Base.metadata.create_all()` and inserts demo clinic
data idempotently.

Availability is derived from recurring doctor schedules, blocked periods, existing
appointments, clinic timezone, and slot duration. The partial unique index
`one_active_appointment_per_doctor_slot` prevents concurrent double-booking.
