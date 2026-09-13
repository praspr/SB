# sb web

Personal assistant dashboard — React + TypeScript + Vite, mock data only (backend wiring later).

## Run

```bash
cd sb/web
npm install
npm run dev
```

Open the printed URL (usually http://localhost:5173).

## Routes

- `/` — Landing: today's todos, today's meetings, quick add
- `/todos` — full task list with status/priority filters
- `/meetings` — today + next 7 days, grouped by date
- `/webex` — DMs, mentions, active spaces

## Shortcuts

- `⌘K` / `Ctrl+K` — command palette
- `⌘N` / `Ctrl+N` — add todo dialog

All data is mocked in `src/lib/mock-data.ts` and served through `src/lib/queries.ts` react-query hooks with an artificial 200ms delay.
