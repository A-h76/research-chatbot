# Brand fonts (optional)

The SPA used to load **Creato Display** from this folder:

- `CreatoDisplay-Light.otf`
- `CreatoDisplay-Regular.otf`
- `CreatoDisplay-Medium.otf`
- `CreatoDisplay-Bold.otf`

Those files are **not** in git (license / missing assets). Until you drop the OTFs here and restore `@font-face` in `frontend/src/index.css`, the app uses **Plus Jakarta Sans** (Google Fonts), matching the marketing landing.

Served in production as `/static/fonts/<filename>` via Flask’s `static/` folder.
