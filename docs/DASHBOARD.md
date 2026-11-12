# Dashboard design notes

## Direction
- Product: a student's daily study decision, with the reasoning visible.
- Character: calm, precise, grounded.
- World: an exam-preparation workbook.
- Moments: the recommended study session and the comparison of four actions.
- Signature: numbered concepts shared by the form, probabilities and focus recommendation.

The starter was an unfinished four-card grid with generic spacing, equal visual
weight and a mock response. The implementation uses neutral surfaces, restrained
green, a consistent 4px spacing rhythm, serif display headings and tabular figures.
Evidence, inference, decision and calendar sections retain their logical order.
The utility chart leads; posterior estimates use smaller bars. Motion is limited
to hover feedback, with reduced-motion support. There are no generated images.

Design guidance: [Unslop](https://github.com/heydamir/unslop), by
[Damir Sokolovsky](https://x.com/heydamir), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The guidance was adapted to this original coursework interface; no example UI
code or reference artwork was copied.

The dashboard is a preview. It writes only to an in-memory calendar, plans today
only, and does not access Google OAuth tokens. The week displays today's session
and the exam date where applicable; future days are explicitly not planned.
