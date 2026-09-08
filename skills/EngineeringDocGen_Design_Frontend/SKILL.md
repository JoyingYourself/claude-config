---
name: EngineeringDocGen_Design_Frontend
description: Create distinctive, production-grade frontend interfaces with high design quality. Use for "design X", "make this beautiful", "redesign UI", "create a landing page".
---

# /EngineeringDocGen_Design_Frontend — production-grade frontend design

Create distinctive, production-grade frontend interfaces. Spec-first: audit → design brief → build → critique loop.

## Core principles

- **Anti-slop**: No Inter/Roboto defaults, purple gradients, glow borders, donut charts, equal 3-card rows
- **Typography**: Prefer Geist, Outfit, Cabinet Grotesk, Satoshi, Source Sans 3 over Inter
- **Color**: Charcoals, graphite, olive, rust, sand, oxblood. No blue-purple gradients, no cyan-on-navy
- **One accent**: Max one, saturation <80%. No AI-purple/blue glow default
- **Dashboard**: Text-first state indicators, left-aligned tables, no fake charts, density-first
- **Dark mode**: Off-black canvas (tinted), depth by lightness, 4+ tinted surfaces

## Modes

| Signal | Mode |
|---|---|
| New UI / landing | CREATE — full design loop |
| Redesign existing | REDESIGN — audit existing then apply |
| Tokens / theme only | SYSTEM — token file + sample |
| Review only | AUDIT — report findings |

## Loop

1. **Audit** — What's working? What violates anti-slop?
2. **Design brief** — Kind, audience, vibe, dials
3. **Build** — Palette, type, spacing, implementation
4. **Critique** — Contrast, consistency, edge states
5. **Verify** — Render check, report
