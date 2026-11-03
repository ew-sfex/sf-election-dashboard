# San Francisco 2026 Election Results Dashboard

Live election results dashboard and article-embed chart system for the **November 3, 2026 San Francisco Consolidated General Election**, built for the *San Francisco Examiner*.

## Four URL Views (One Codebase)

1. **Full Public Dashboard (`/`)**
   - Category-level accordions with **Board of Supervisors**, **SF Ballot Measures**, **U.S. Congress & State Legislature**, and **Education Boards & Citywide Offices** expanded by default, and **Statewide Offices**, **Statewide Propositions**, and **Judicial Confirmations** collapsed by default.
   - Instant search bar (auto-expands matching sections) and `Expand All / Collapse All` controls.
   - Explicit **"SF Votes Only"** badges and disclaimers on every multi-county district (U.S. House D11 & D15, State Assembly D17 & D19, BART D8, BOE D2) and every statewide race/proposition.
   - No embed buttons or editorial chrome on reader-facing views.

2. **Truncated Board of Supervisors Roundup (`/?view=supervisors`)**
   - Displays all 5 Supervisor races (Districts 2, 4, 6, 8, and 10) in a clean 2-column grid for roundup articles or homepage modules. (`/?view=measures` is also available for local ballot measures.)

3. **Individual Race Article Embeds (`/?race=<slug>`)**
   - Chromeless single-race horizontal bar chart (or comma-separated group like `/?race=bos-d2,bos-d4`) that automatically posts its scroll height to the parent window via `postMessage`.
   - Stacked candidate rows automatically sort top-to-bottom by total votes as returns arrive.
   - **SF Examiner two-tone bars:** `#EAB308` (Mail) + `#FDE047` (Election Day) for the leading choice (or top 3 in 3-seat School/College Board races), and `#4B5563` (Mail) + `#9CA3AF` (Election Day) for other choices.

4. **Internal Newsroom Embed Directory (`/?view=embeds`)**
   - Searchable directory of all 62 active contests + the Supervisors roundup with live previews and one-click `<iframe>` copy buttons.

## Simulation / Pre-Election Preview Mode

Append `&demo=25`, `&demo=50`, `&demo=75`, or `&demo=100` (or `?demo=100` on the root URL) to preview realistic 2026 vote progression and bar sorting before polls close on Tuesday, November 3, 2026 (~8:45 PM PST first drop).

## Development

```bash
cd src/frontend/dashboard
npm install
npm run dev
```
