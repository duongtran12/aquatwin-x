# AquaTwin-X Dashboard

React dashboard for visualizing the demo water network, simulating a pipe leak, testing manual valve isolation and requesting a Genetic Algorithm recovery plan.

## Run locally

Start the FastAPI service from the project root:

```powershell
uvicorn backend.app.main:app --reload
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dashboard connects to `http://localhost:8000` by default.

To use another API origin, create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

## Production check

```powershell
npm run build
npm run preview
```

The production bundle is written to `frontend/dist` and is intentionally ignored by Git.
