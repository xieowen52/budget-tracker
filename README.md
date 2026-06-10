# Budget Tracker

A personal finance web app with AI-powered transaction parsing. Describe a purchase in plain English and Claude extracts the amount, category, and date automatically.

<!-- Replace with your dashboard screenshot -->
<img width="911" height="646" alt="image" src="https://github.com/user-attachments/assets/b3fc883a-d6a7-4ecd-b346-8ffbffcd88d5" />
<img width="917" height="761" alt="image" src="https://github.com/user-attachments/assets/a30127c0-112f-4b7c-9de4-42f2bc7af17e" />
<img width="913" height="767" alt="image" src="https://github.com/user-attachments/assets/b6d94645-2591-454c-b196-b01c0873bacd" />
<img width="911" height="776" alt="image" src="https://github.com/user-attachments/assets/96dedb23-2f19-428b-8664-42097bd2ad59" />


## Features

- **AI transaction parsing** — type "spent $23 on Uber last night" and Claude structures it for you, with a confirm step before saving
- **Dashboard** — monthly summary cards (income, expenses, net, savings rate) with spending breakdown by category
- **Charts** — bar, pie, and donut views for spending by category; yearly income vs. expenses overview
- **Budget tracking** — set monthly limits per category and track progress
- **Month navigation** — browse any past month's data
- **Manual entry** — full form with category, date, and optional description

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11 |
| Database | Supabase (PostgreSQL + Row Level Security) |
| Auth | Custom JWT (bcrypt + python-jose) |
| AI | Anthropic Claude API (`claude-sonnet-4-6`) |

## Local Setup

**Prerequisites:** Python 3.11, Node.js 18+

**1. Clone the repo**
```bash
git clone https://github.com/xieowen52/budget-tracker.git
cd budget-tracker
```

**2. Backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
JWT_SECRET=any_long_random_string
ANTHROPIC_API_KEY=your_anthropic_key   # optional — omit to disable AI parsing
ALLOWED_ORIGINS=http://localhost:5173
```

```bash
uvicorn app.main:app --reload
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev
# App running at http://localhost:5173
```

## Design Decisions

**Parse → confirm flow** — AI parsing populates a form rather than saving directly. This keeps the user in control and avoids silent data errors when Claude misreads ambiguous input.

**Service-role key + manual RLS** — the backend holds the Supabase service-role key and enforces authorization in route handlers, rather than relying on Supabase's client-side auth. This gives full control over access logic and keeps the architecture explicit.

**JWT over sessions** — stateless tokens work cleanly with a separate frontend/backend deployment without needing shared session storage.
