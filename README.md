# School Management System

A complete, production-oriented School ERP built with Django 5.2 + Django REST Framework + SimpleJWT and React 18 + TypeScript + Vite + Tailwind + shadcn/ui. Tenants (schools) are strictly isolated; role-based access control, audit logs and immutable money operations are enforced end-to-end.

## Tech Stack

**Backend**
- Django 5.2 LTS, Django REST Framework, SimpleJWT, django-filter, drf-spectacular
- PostgreSQL (primary), SQLite (convenient local dev via DATABASE_URL)
- Celery + Redis (optional), django-cors-headers, whitenoise, Pillow, python-dotenv, dj-database-url

**Frontend**
- React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Radix UI + lucide-react
- React Router, TanStack Query, React Hook Form + Zod, Axios, date-fns, sonner, recharts

## Project Structure

```
School/
├── backend/
│   ├── school_project/    # Project settings, URLs, WSGI/ASGI
│   ├── accounts/          # Custom user, auth, login audit
│   ├── core/              # Shared models/mixins/permissions/services
│   ├── schools/           # Tenant config (school, session, grade, section)
│   ├── admissions/        # Applications & documents
│   ├── students/          # Students, guardians, documents
│   ├── academics/         # Subjects, class subjects, enrollments
│   ├── attendance/        # Student/staff attendance + corrections
│   ├── timetable/         # Rooms, periods, entries
│   ├── examinations/       # Exams, marks, report cards
│   ├── finance/            # Fees, invoices, payments, discounts, refunds
│   ├── assignments/       # Assignments & submissions
│   ├── communications/    # Announcements, notifications, messages
│   ├── library/           # Books, borrowings, fines
│   ├── hr/                # Staff, contracts, leave
│   ├── transport/         # Vehicles, routes, assignments
│   ├── reports/           # Role-aware analytics & CSV export
│   ├── audit/             # Audit & activity logs + middleware
│   └── manage.py
├── frontend/             # Vite + React SPA
├── _gen/                 # Code generators (for reference)
└── docs/                 # Detailed documentation
```

## Getting Started

### Prerequisites
- Python 3.12+ (project uses 3.13)
- Node.js 20+ and npm
- PostgreSQL (or use SQLite via DATABASE_URL)

### Backend Setup
1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt  # or install packages directly
   ```
3. Configure environment:
   ```bash
   cp .env.example .env  # or create backend/.env
   # For local dev without Postgres, set DATABASE_URL=sqlite:///backend/db.sqlite3
   ```
4. Run migrations and seed demo data:
   ```bash
   cd backend
   python manage.py migrate
   python manage.py create_default_superuser  # or set DJANGO_SUPERUSER_* env vars
   python manage.py seed_demo
   ```
5. Run the server:
   ```bash
   python manage.py runserver
   ```
6. API docs: http://localhost:8000/api/docs/

### Frontend Setup
1. Install and run:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Build for production:
   ```bash
   npm run build
   ```

## Key Features
- **Tenant isolation**: All school-scoped models enforced via `SchoolScopedQuerysetMixin`; superadmins may inspect other schools explicitly.
- **RBAC**: 10 roles with server-side permission classes; UI is not authoritative.
- **Money safety**: Decimal only, transactional operations, locks (`select_for_update`) and immutable audit trails.
- **Library**: borrow/return with guards, available copies tracking, fines, reservations.
- **Attendance**: idempotent bulk upsert with `AttendanceCorrection` audit.
- **Exams**: mark entry with validation, automatic report card computation and ranking.
- **Finance**: invoice generation, payments with balance checks, refund tracking.
- **Audit**: activity middleware and read-only audit log endpoints.
- **Reports**: role-aware dashboard, trends, CSV exports per dataset.
- **Idempotent seeding**: `seed_demo` recreates demo school safely and sets predictable credentials.

## Demo Credentials
After seeding, use any of the listed accounts with password `Demo@12345` (or the `DEMO_PASSWORD` you set). The superuser defaults to `superadmin`.

## Security Notes
- Secrets must never be committed; use `.env`.
- Cross-school access is blocked for regular users.
- IDOR protection via object-level checks and school scoping.
- Published exam results are locked for unauthorized roles.
- Safe file uploads (size/type constraints) for assignments/submissions.
- Audit trail for sensitive write operations.

## Running Tests
```bash
cd backend
python -m pytest
```

## Documentation
Additional deep-dive docs live under `docs/` (architecture, API, deployment, environment, tests, demo data, security, phased checklist, migrations, backup/restore).

## Notes
- SQLite works for local dev if Postgres is unavailable; production must use PostgreSQL.
- All timestamps use timezone-aware datetimes; dates are `date` fields.
- `money()` quantizes to 2 decimals via `Decimal.quantize(ROUND_HALF_UP)`.
- Migrations are tracked in each app's `migrations/`.
- Stale `__pycache__` and non-UTF8 files can break imports — the project was hardened to avoid these issues.
