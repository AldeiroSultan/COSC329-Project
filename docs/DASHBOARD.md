# Dashboard design notes

## Direction
- Product: a student's daily study decision, with the reasoning shown.
- Style: neumorphic. Every surface is either raised (cards, buttons, the selected option) or
  pressed in (inputs, tracks, charts' wells), lit by one pair of light and dark shadows. A light
  theme and a dark theme use the same components with different colour tokens.
- Reference: two neumorphic dashboard concept images supplied by the team (a light blue-grey one
  and a dark charcoal-and-orange one) set the mood. No artwork or code was copied.
- Text: labels only where they carry information. There are no slogans, section numbers or
  explanatory captions; explanation lives in the guided tour instead.
- Icons: a small inline SVG set (`<symbol>` sprite in `web/index.html`). No emoji, no icon font,
  no external libraries or web fonts, so the page works offline.

An earlier version of the dashboard was informed by Unslop (Damir Sokolovsky, CC BY 4.0). The
current design no longer uses that guidance.

## Files
| File | Job |
|---|---|
| `web/index.html` | Page structure, icon sprite, theme script that runs before first paint |
| `web/styles.css` | Light/dark colour tokens, raised/pressed components, tour overlay, responsive rules |
| `web/app.js` | Form, rendering, theme switch, help menu, the app tour and the three guided examples |
| `web/tour.js` | Generic spotlight engine: dims the page, highlights one element, points a card at it |

## Guided tour
- **First visit:** the app tour starts by itself once (remembered in `localStorage`).
- **? button:** opens a menu with *App tour* and three *Guided examples*.
- **Spotlight:** the target is cut out of a dimmed page and ringed in the accent colour; a card with
  a pointer sits beside it (below or above if there is no room, docked to the bottom on phones).
- **Guided examples** (struggling student, well-prepared student, one weak concept) fill in the form
  step by step, press Calculate, and read the real result back: beliefs, action scores, the decision,
  the calendar, then a summary of Student, Beliefs, Decision and Why. The one-line takeaway is shown
  only when the planner picks the action the example is meant to illustrate.
- **Keyboard:** Next and Back buttons, left/right arrow keys, Esc to leave, focus kept inside the card
  and returned to the **?** button afterwards. Screen readers hear each step as it changes.

## Accessibility and motion
- Both themes meet WCAG AA text contrast (checked in `tests/test_dashboard_assets.py`).
- Segmented controls are real radio buttons with visible focus rings; the theme control is a `switch`.
- `prefers-reduced-motion` turns off transitions, the pulse and smooth scrolling.
- Touch targets are at least 44 px.

## Scope
The dashboard is a preview. It writes only to an in-memory calendar, plans today only, and does not
access Google OAuth tokens. The week shows today's session and the exam date where applicable; other
days are left empty because the planner decides one day at a time.
