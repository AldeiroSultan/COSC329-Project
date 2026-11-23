# Dashboard design notes

## Direction
- Product: a student's daily study decision, with the reasoning shown.
- Style: neumorphic. Every surface is either raised (cards, buttons, the selected option) or
  pressed in (inputs, tracks, charts' wells), lit by one pair of light and dark shadows. A light
  theme and a dark theme use the same components with different colour tokens.
- Colour: warm ivory and beige with forest and sage green in the light theme; deep green-black with
  sage in the dark theme. A terracotta tone is used only for stress, so risk reads differently from
  progress. A faint paper grain sits behind everything.
- Type: Lexend Deca throughout, the geometric sans HubSpot uses for its headlines (HubSpot's own
  typeface is not publicly licensed). Headings are semi-bold and large figures medium weight, with
  slightly tightened letter spacing. It loads from Google Fonts; if it cannot load, the system sans
  (Segoe UI, San Francisco, etc.) is used instead.
- Focal point: a dark-green hero card holds the recommendation and study time. Pass chance and
  stress risk are dial gauges. Figures count up and bars grow when a plan is calculated (skipped
  when the system asks for reduced motion).
- Reference: two neumorphic dashboard concept images supplied by the team (a light blue-grey one
  and a dark charcoal-and-orange one) set the mood. No artwork or code was copied.
- Text: labels only where they carry information. There are no slogans, section numbers or
  explanatory captions; explanation lives in the guided tour instead.
- Icons: a small inline SVG set (`<symbol>` sprite in `web/index.html`). No emoji, no icon font and
  no JavaScript libraries. The only outside request is the Lexend Deca font; everything else works offline.

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
  the calendar, then a short summary. The wording is written as connected sentences ("because of
  that", "which means") and is generated from the real result, so it always matches what the planner
  decided. The summary opens with a plain recommendation (for example "Do an intense 5-hour study
  block today"), explains what the scores mean in words, and says when the choice is a close call.
- **Summary card:** a wide landscape card. On the left are a recommendation headline, then two labelled
  paragraphs ("The situation", "What it means") with the figures picked out in colour, and a short next
  step. On the right, in a pressed well, are two gauges (pass chance, stress risk), the study time as a
  dark-green chip, and the four action scores as bars with a "close call" or "clear winner" chip. On a
  phone it becomes one column and the graphics come straight after the headline.
- **Segmented buttons** (Easy / Medium / Hard, Unknown / Low / High, and so on): a raised pill slides
  to the chosen option, also when a guided example fills the form. It slides briefly even when the
  system asks for reduced motion.
- **Theme switch:** the knob slides, the sun and moon turn over, and the new theme spreads out as a
  circle from the switch (browsers without view transitions, and people who prefer reduced motion,
  get a colour fade instead; the knob still slides).
- **Keyboard:** Next and Back buttons, left/right arrow keys, Esc to leave, focus kept inside the card
  and returned to the **?** button afterwards. Screen readers hear each step as it changes.

## Caching
The server tells browsers to re-check the page, scripts and styles on every load
(`Cache-Control: no-cache`; unchanged files still answer 304), and the asset URLs carry a version
(`?v=4`). This stops a browser from mixing a new page with an old cached script or stylesheet.
If you change a file in `web/`, raise the version in `index.html` and the import in `app.js`.

## Accessibility and motion
- Both themes meet WCAG AA text contrast (checked in `tests/test_dashboard_assets.py`).
- Segmented controls are real radio buttons with visible focus rings; the theme control is a `switch`.
- `prefers-reduced-motion` turns off transitions, the pulse and smooth scrolling.
- Touch targets are at least 44 px.

## Scope
The dashboard is a preview. It writes only to an in-memory calendar, plans today only, and does not
access Google OAuth tokens. The week shows today's session and the exam date where applicable; other
days are left empty because the planner decides one day at a time.
