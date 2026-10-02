---
name: react-vite-dashboard
description: Use this skill when building the React diagnostic dashboard, frontend components, WebSocket connection to the backend, or real-time telemetry visualisation
---

# React 18 + Vite Dashboard Patterns

## Core Rules
- React 18 — use `createRoot`, not `ReactDOM.render`
- State: `useState` + `useReducer` for local, no Redux needed at this scale
- WebSocket connection lives in a custom hook, not scattered in components
- All API calls go through a single `api.js` module
- No external UI component library — Vanilla CSS only (see CSS skill)

## Vite Project Bootstrap
```bash
npm create vite@latest dashboard -- --template react
cd dashboard && npm install
```

## WebSocket Hook (receives scheduler events from FastAPI)
```javascript
// hooks/useSchedulerSocket.js
import { useEffect, useState } from 'react'

export function useSchedulerSocket() {
  const [events, setEvents] = useState([])

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)
      setEvents(prev => [event, ...prev].slice(0, 100))
    }
    return () => ws.close()
  }, [])

  return events
}
```

## API Module
```javascript
// api.js
const BASE = 'http://localhost:8000/api'

export const createSession = (body) =>
  fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json())

export const getSessions = () =>
  fetch(`${BASE}/sessions`).then(r => r.json())
```

## Node State Badge Component Pattern
```jsx
const STATE_COLORS = {
  ACTIVE_PHYSICAL_LINK: '#5DCAA5',
  PAUSED_QUEUED:        '#AFA9EC',
  CONNECTING:           '#F0C97B',
  DEGRADED:             '#F0997B',
  UNINITIALIZED:        '#B4B2A9',
}

function NodeBadge({ nodeId, state }) {
  return (
    <span className="node-badge" style={{ background: STATE_COLORS[state] }}>
      {nodeId} · {state}
    </span>
  )
}
```

## Anti-patterns
- Never use class components — only functional + hooks
- Never fetch inside a component body — always inside `useEffect` or a custom hook
- Never install a UI library (MUI, Ant, Chakra) — Vanilla CSS only