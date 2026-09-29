# TISC 2026 Casebook

Writeups for Levels 1–7 of [TISC 2026](https://www.csit.gov.sg/) (The InfoSecurity Challenge), by **Elodie Ng**.

I'm a psychology student, and programming isn't my strength. This site covers each level's solution and,
for Level 4 (ZyGPT) and Level 7 (Omnitrix), the workings: everything I tried before the solve landed.
I used AI heavily, and the site says how, level by level.

**Read it here:** https://queryoptimiser.github.io/tisc-2026/

## What's inside

| Level | Challenge | Category |
| :---: | --- | --- |
| 1 | REDACTED | Forensics |
| 2 | My Printer has a Secret | Forensics / OSINT |
| 3 | Lion City Layover | Web / reversing / crypto |
| 4 | ZyGPT | Crypto / AI |
| 5 | Trash Talk DS | Misc |
| 6 | Provenance | Reverse engineering |
| 7 | Omnitrix | Pwn |

My own solve scripts are in `public/code/`. Challenge files are not redistributed.

## Running it locally

```bash
npm install
npm run dev        # http://localhost:4321/tisc-2026/
npm run build      # static site in dist/
```

Pages are Markdown files in `src/pages/levels/`.
Pushing to `main` deploys to GitHub Pages through `.github/workflows/deploy.yml`.
