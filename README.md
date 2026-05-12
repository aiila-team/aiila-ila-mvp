# OSINT MVP Frontend

React + TypeScript + Vite frontend for the OSINT platform.

## Stack

- **React 18** with TypeScript (`.tsx`)
- **Vite 5** — ultra-fast HMR bundler
- **Tailwind CSS 3** — utility-first styling
- **Zustand** — lightweight state management
- **Axios** — HTTP client with interceptors
- **React Router 6** — client-side routing

## Project Structure

```
src/
├── api/
│   ├── client.ts         # Axios instance + auth interceptors
│   └── alerts.ts         # Alert API methods
├── components/
│   ├── AlertCard.tsx
│   ├── EntityCard.tsx
│   ├── RiskScoreBadge.tsx
│   ├── RiskGauge.tsx
│   ├── GraphVisualization.tsx
│   ├── Sidebar.tsx
│   ├── TopNav.tsx
│   └── SearchBar.tsx
├── hooks/
│   ├── useAlertStream.ts  # WebSocket auto-reconnect hook
│   ├── useEntities.ts
│   └── useGraph.ts
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── AlertInbox.tsx
│   ├── EntitiesPage.tsx
│   ├── EntityProfile.tsx
│   ├── KeywordManager.tsx
│   ├── SourceMonitor.tsx
│   └── Investigation.tsx
├── store/
│   └── index.ts           # Zustand stores (auth, alerts, entities, UI)
├── types/
│   └── index.ts           # All shared TypeScript interfaces
└── main.tsx               # App root + router
```

## Getting Started

```bash
# Install dependencies
npm install

# Copy env file and configure
cp .env.example .env

# Start dev server
npm run dev

# Build for production
npm run build
```

## TypeScript Notes

- `strict: false` — relaxed mode for migration safety
- `noImplicitAny: false` — allows gradual typing
- All major types defined in `src/types/index.ts`
- Use `any` sparingly and replace with proper types over time

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `/api` | Backend REST API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/ws` | WebSocket endpoint |
