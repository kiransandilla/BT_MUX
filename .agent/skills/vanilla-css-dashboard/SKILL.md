---
name: vanilla-css-dashboard
description: Use this skill when writing any CSS for the diagnostic dashboard, layout, node state colours, telemetry panels, or responsive design
---

# Vanilla CSS Patterns for BT-Mux Dashboard

## Core Rules
- No Tailwind, no CSS-in-JS, no component libraries — plain `.css` files only
- Use CSS custom properties (variables) for all colours and spacing
- Layout: CSS Grid for page structure, Flexbox for component internals
- Dark theme by default — diagnostic tools live in dark environments

## CSS Variables (put in `:root`)
```css
:root {
  /* colours */
  --bg-primary:    #0f0f14;
  --bg-surface:    #1a1a24;
  --bg-card:       #22222f;
  --border:        #2e2e40;
  --text-primary:  #e8e8f0;
  --text-muted:    #7a7a96;

  /* node state colours — match UML diagrams */
  --state-active:  #5DCAA5;
  --state-paused:  #AFA9EC;
  --state-connect: #F0C97B;
  --state-degraded:#F0997B;
  --state-uninit:  #B4B2A9;

  /* spacing scale */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 40px;
}
```

## Page Layout (CSS Grid)
```css
.dashboard {
  display: grid;
  grid-template-columns: 1fr 320px;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    "header  header"
    "main    sidebar";
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}
```

## Card Pattern
```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: var(--space-md);
}
```

## Node Badge
```css
.node-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 3px 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 600;
  color: #0f0f14;
}
```

## Telemetry Metric
```css
.metric {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}
.metric__label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; }
.metric__value { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }
```

## Anti-patterns
- Never use `px` for font sizes on body text — use `rem`
- Never hardcode colour hex values outside `:root` variables
- Never use `!important`
- Never install Tailwind or any CSS framework