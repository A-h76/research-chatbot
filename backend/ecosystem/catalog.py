"""Research ecosystem Integrations catalog — single source of truth.

Thin facade over adapters / connections / env. No duplicate token tables.
Register a provider here → Settings + Landing consume the same rows.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

# Ordered categories (Settings + Landing).
CATEGORIES: list[tuple[str, str, str]] = [
    ("reference_managers", "Reference Managers", "Bring the library you already maintain."),
    ("academic_sources", "Academic Sources", "Discover and enrich from scholarly networks."),
    ("cloud_storage", "Cloud Storage", "Sync libraries from shared drives."),
    ("writing", "Writing", "Draft where your team already writes."),
    ("ai", "AI", "Model routing for research tasks."),
    ("developer", "Developer", "Extend Dhund into your stack."),
    ("identity", "Identity", "Sign-in and researcher identity."),
]

CAPABILITY_KEYS = ("import", "sync", "pdf_pull", "folder_watch", "write_back")


def _caps(
    *,
    import_files: bool = False,
    sync: bool = False,
    pdf_pull: bool = False,
    folder_watch: bool = False,
    write_back: bool = False,
) -> dict[str, bool]:
    return {
        "import": bool(import_files),
        "sync": bool(sync),
        "pdf_pull": bool(pdf_pull),
        "folder_watch": bool(folder_watch),
        "write_back": bool(write_back),
    }


def _env_set(*names: str) -> bool:
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        if str(raw).strip().strip('"').strip("'"):
            return True
    return False


def _provider(
    *,
    id: str,
    name: str,
    category: str,
    availability: str,
    auth: str,
    capabilities: dict[str, bool] | None = None,
    brand_color: str = "#0F6E6A",
    logo: str = "",
    mark: str = "",
    blurb: str = "",
    docs_url: str = "",
    actions: dict[str, Any] | None = None,
    connectable: bool = False,
    server_configured_check: Callable[[], bool] | None = None,
    landing: bool = True,
) -> dict[str, Any]:
    assert availability in {"live", "soon", "not_planned"}
    assert auth in {"oauth", "api_key", "none", "file"}
    assert category in {c[0] for c in CATEGORIES}
    caps = capabilities or _caps()
    return {
        "id": id,
        "name": name,
        "category": category,
        "availability": availability,
        "auth": auth,
        "capabilities": caps,
        "supported_features": [k for k, v in caps.items() if v],
        "brand_color": brand_color,
        "logo": logo,
        "mark": mark,
        "blurb": blurb,
        "docs_url": docs_url,
        "actions": actions or {},
        "connectable": connectable,
        "server_configured_check": server_configured_check,
        "landing": landing,
    }


def _zotero_configured() -> bool:
    from backend.library import zotero as zotero_mod

    return zotero_mod.zotero_configured()


def _mendeley_configured() -> bool:
    from backend.library import mendeley as mendeley_mod

    return mendeley_mod.mendeley_configured()


def _drive_configured() -> bool:
    from backend.library import google_drive as drive_mod

    return drive_mod.drive_configured()


def _dropbox_configured() -> bool:
    from backend.library import dropbox as dropbox_mod

    return dropbox_mod.dropbox_configured()


def _onedrive_configured() -> bool:
    from backend.library import onedrive as onedrive_mod

    return onedrive_mod.onedrive_configured()


PROVIDER_DEFS: list[dict[str, Any]] = [
    _provider(
        id="zotero",
        name="Zotero",
        category="reference_managers",
        availability="live",
        auth="oauth",
        capabilities=_caps(import_files=True, sync=True, pdf_pull=True),
        brand_color="#CC2936",
        logo="brands/zotero.svg",
        blurb="Import collections, incremental sync, and pull attached PDFs.",
        docs_url="https://www.zotero.org/support/dev/web_api/v3/basics",
        connectable=True,
        server_configured_check=_zotero_configured,
        actions={
            "connect": {"method": "GET", "path": "/api/library/zotero/connect"},
            "disconnect": {"method": "POST", "path": "/api/library/zotero/disconnect"},
            "sync": {"method": "POST", "path": "/api/library/zotero/sync"},
            "pull_pdfs": {"method": "POST", "path": "/api/library/zotero/pull-pdfs"},
            "deep_link": "/library?provider=zotero#import",
        },
    ),
    _provider(
        id="mendeley",
        name="Mendeley",
        category="reference_managers",
        availability="live",
        auth="oauth",
        capabilities=_caps(import_files=True, sync=True, pdf_pull=True),
        brand_color="#A60000",
        logo="brands/mendeley.svg",
        blurb="Import folders, incremental sync, and pull attached PDFs.",
        docs_url="https://dev.mendeley.com/",
        connectable=True,
        server_configured_check=_mendeley_configured,
        actions={
            "connect": {"method": "GET", "path": "/api/library/mendeley/connect"},
            "disconnect": {"method": "POST", "path": "/api/library/mendeley/disconnect"},
            "sync": {"method": "POST", "path": "/api/library/mendeley/sync"},
            "pull_pdfs": {"method": "POST", "path": "/api/library/mendeley/pull-pdfs"},
            "deep_link": "/library?provider=mendeley#import",
        },
    ),
    _provider(
        id="bibtex",
        name="BibTeX",
        category="reference_managers",
        availability="live",
        auth="file",
        capabilities=_caps(import_files=True),
        brand_color="#0F6E6A",
        mark="BIB",
        blurb="Paste or upload a .bib file into Library.",
        actions={"deep_link": "/library#import"},
    ),
    _provider(
        id="ris",
        name="RIS",
        category="reference_managers",
        availability="live",
        auth="file",
        capabilities=_caps(import_files=True),
        brand_color="#0F6E6A",
        mark="RIS",
        blurb="Paste or upload a .ris file into Library.",
        actions={"deep_link": "/library#import"},
    ),
    _provider(
        id="endnote",
        name="EndNote",
        category="reference_managers",
        availability="soon",
        auth="oauth",
        brand_color="#ED6C06",
        mark="EN",
    ),
    _provider(
        id="paperpile",
        name="Paperpile",
        category="reference_managers",
        availability="soon",
        auth="oauth",
        brand_color="#2D72D2",
        mark="PP",
    ),
    _provider(
        id="readcube",
        name="ReadCube",
        category="reference_managers",
        availability="soon",
        auth="oauth",
        brand_color="#00A3E0",
        mark="RC",
    ),
    _provider(
        id="jabref",
        name="JabRef",
        category="reference_managers",
        availability="soon",
        auth="file",
        brand_color="#2C6EAF",
        mark="JR",
    ),
    _provider(
        id="openalex",
        name="OpenAlex",
        category="academic_sources",
        availability="live",
        auth="none",
        capabilities=_caps(import_files=True),
        brand_color="#EB6019",
        mark="OA",
        blurb="Discover works and import stubs from Search.",
        actions={"deep_link": "/search?mode=discover"},
    ),
    _provider(
        id="crossref",
        name="Crossref",
        category="academic_sources",
        availability="live",
        auth="none",
        brand_color="#3EB1C8",
        mark="XR",
        blurb="DOI metadata enrichment for library papers.",
    ),
    _provider(
        id="semantic_scholar",
        name="Semantic Scholar",
        category="academic_sources",
        availability="live",
        auth="none",
        brand_color="#1857B6",
        logo="brands/semanticscholar.svg",
        blurb="Related work and citation enrichment.",
    ),
    _provider(
        id="pubmed",
        name="PubMed",
        category="academic_sources",
        availability="live",
        auth="none",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#326599",
        logo="brands/pubmed.svg",
        blurb="Search PubMed and import into Library → Analysis 2.0. Optional NCBI_API_KEY raises rate limits.",
        actions={"deep_link": "/search?mode=discover&provider=pubmed"},
    ),
    _provider(
        id="arxiv",
        name="arXiv",
        category="academic_sources",
        availability="live",
        auth="none",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#B31B1B",
        logo="brands/arxiv.svg",
        blurb="Search arXiv preprints and import PDFs into Library → Analysis 2.0.",
        actions={"deep_link": "/search?mode=discover&provider=arxiv"},
    ),
    _provider(
        id="europe_pmc",
        name="Europe PMC",
        category="academic_sources",
        availability="live",
        auth="none",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#F15A29",
        mark="EP",
        blurb="Search Europe PMC and import OA PDFs into Library → Analysis 2.0.",
        actions={"deep_link": "/search?mode=discover&provider=europe_pmc"},
    ),
    _provider(
        id="ssrn",
        name="SSRN",
        category="academic_sources",
        availability="soon",
        auth="none",
        brand_color="#1B4F72",
        logo="brands/ssrn.svg",
    ),
    _provider(
        id="ieee_xplore",
        name="IEEE Xplore",
        category="academic_sources",
        availability="soon",
        auth="api_key",
        brand_color="#00629B",
        logo="brands/ieee.svg",
    ),
    _provider(
        id="acm_dl",
        name="ACM Digital Library",
        category="academic_sources",
        availability="soon",
        auth="api_key",
        brand_color="#1D78C1",
        logo="brands/acm.svg",
    ),
    _provider(
        id="google_drive",
        name="Google Drive",
        category="cloud_storage",
        availability="live",
        auth="oauth",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#4285F4",
        logo="brands/googledrive.svg",
        blurb="Import PDFs from Drive into Library → Analysis 2.0. Folder watch later.",
        connectable=True,
        server_configured_check=_drive_configured,
        actions={
            "connect": {"method": "GET", "path": "/api/library/google_drive/connect"},
            "disconnect": {"method": "POST", "path": "/api/library/google_drive/disconnect"},
            "deep_link": "/library?provider=google_drive#import",
        },
    ),
    _provider(
        id="dropbox",
        name="Dropbox",
        category="cloud_storage",
        availability="live",
        auth="oauth",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#0061FF",
        logo="brands/dropbox.svg",
        blurb="Import PDFs from Dropbox into Library → Analysis 2.0. Folder watch later.",
        connectable=True,
        server_configured_check=_dropbox_configured,
        actions={
            "connect": {"method": "GET", "path": "/api/library/dropbox/connect"},
            "disconnect": {"method": "POST", "path": "/api/library/dropbox/disconnect"},
            "deep_link": "/library?provider=dropbox#import",
        },
    ),
    _provider(
        id="onedrive",
        name="OneDrive",
        category="cloud_storage",
        availability="live",
        auth="oauth",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#0078D4",
        logo="brands/microsoftonedrive.svg",
        blurb="Import PDFs from OneDrive into Library → Analysis 2.0. Folder watch later.",
        connectable=True,
        server_configured_check=_onedrive_configured,
        actions={
            "connect": {"method": "GET", "path": "/api/library/onedrive/connect"},
            "disconnect": {"method": "POST", "path": "/api/library/onedrive/disconnect"},
            "deep_link": "/library?provider=onedrive#import",
        },
    ),
    _provider(
        id="box",
        name="Box",
        category="cloud_storage",
        availability="soon",
        auth="oauth",
        capabilities=_caps(folder_watch=True, import_files=True),
        brand_color="#0061D5",
        logo="brands/box.svg",
    ),
    _provider(
        id="writing_studio",
        name="Writing Studio",
        category="writing",
        availability="live",
        auth="none",
        brand_color="#0F6E6A",
        mark="W",
        blurb="Grounded literature review drafts inside Dhund.",
        actions={"deep_link": "/writing"},
    ),
    _provider(
        id="google_docs",
        name="Google Docs",
        category="writing",
        availability="soon",
        auth="oauth",
        capabilities=_caps(write_back=True),
        brand_color="#4285F4",
        logo="brands/googledocs.svg",
    ),
    _provider(
        id="microsoft_word",
        name="Microsoft Word",
        category="writing",
        availability="soon",
        auth="oauth",
        capabilities=_caps(write_back=True),
        brand_color="#2B579A",
        logo="brands/microsoftword.svg",
    ),
    _provider(
        id="overleaf",
        name="Overleaf",
        category="writing",
        availability="soon",
        auth="oauth",
        capabilities=_caps(write_back=True),
        brand_color="#47A141",
        logo="brands/overleaf.svg",
    ),
    _provider(
        id="notion",
        name="Notion",
        category="writing",
        availability="soon",
        auth="oauth",
        capabilities=_caps(write_back=True),
        brand_color="#000000",
        logo="brands/notion.svg",
    ),
    _provider(
        id="obsidian",
        name="Obsidian",
        category="writing",
        availability="soon",
        auth="file",
        capabilities=_caps(write_back=True),
        brand_color="#7C3AED",
        logo="brands/obsidian.svg",
    ),
    _provider(
        id="openai",
        name="OpenAI",
        category="ai",
        availability="live",
        auth="api_key",
        brand_color="#10A37F",
        logo="brands/openai.svg",
        server_configured_check=lambda: _env_set("OPENAI_API_KEY"),
        blurb="Primary chat and research models.",
    ),
    _provider(
        id="anthropic",
        name="Claude",
        category="ai",
        availability="live",
        auth="api_key",
        brand_color="#D97757",
        logo="brands/anthropic.svg",
        server_configured_check=lambda: _env_set("ANTHROPIC_API_KEY"),
        blurb="Available when ANTHROPIC_API_KEY is configured.",
    ),
    _provider(
        id="gemini",
        name="Gemini",
        category="ai",
        availability="live",
        auth="api_key",
        brand_color="#8E75B2",
        logo="brands/googlegemini.svg",
        server_configured_check=lambda: _env_set("GOOGLE_API_KEY"),
        blurb="Available when GOOGLE_API_KEY is configured.",
    ),
    _provider(
        id="grok",
        name="Grok",
        category="ai",
        availability="soon",
        auth="api_key",
        brand_color="#1DA1F2",
        logo="brands/x.svg",
    ),
    _provider(
        id="deepseek",
        name="DeepSeek",
        category="ai",
        availability="soon",
        auth="api_key",
        brand_color="#4D6BFE",
        logo="brands/deepseek.svg",
    ),
    _provider(
        id="mistral",
        name="Mistral",
        category="ai",
        availability="soon",
        auth="api_key",
        brand_color="#FF7000",
        logo="brands/mistralai.svg",
    ),
    _provider(
        id="open_api",
        name="Open API",
        category="developer",
        availability="soon",
        auth="api_key",
        brand_color="#0F6E6A",
        mark="API",
        blurb="External API keys for ecosystem apps — planned.",
    ),
    _provider(
        id="mcp",
        name="MCP",
        category="developer",
        availability="soon",
        auth="api_key",
        brand_color="#111816",
        mark="MCP",
    ),
    _provider(
        id="zapier",
        name="Zapier",
        category="developer",
        availability="soon",
        auth="oauth",
        brand_color="#FF4A00",
        logo="brands/zapier.svg",
    ),
    _provider(
        id="n8n",
        name="n8n",
        category="developer",
        availability="soon",
        auth="api_key",
        brand_color="#EA4B71",
        logo="brands/n8n.svg",
    ),
    _provider(
        id="webhooks",
        name="Webhooks",
        category="developer",
        availability="soon",
        auth="api_key",
        brand_color="#0F6E6A",
        mark="WH",
    ),
    _provider(
        id="google_oauth",
        name="Google",
        category="identity",
        availability="live",
        auth="oauth",
        brand_color="#4285F4",
        logo="brands/googlescholar.svg",  # letter-G family mark when google.svg absent
        blurb="Sign in with Google.",
        server_configured_check=lambda: _env_set("GOOGLE_CLIENT_ID")
        and _env_set("GOOGLE_CLIENT_SECRET"),
    ),
    _provider(
        id="orcid",
        name="ORCID",
        category="identity",
        availability="live",
        auth="none",
        capabilities=_caps(import_files=True, pdf_pull=True),
        brand_color="#A6CE39",
        logo="brands/orcid.svg",
        blurb="Paste an ORCID iD to import public works. OA PDFs when available; otherwise attach a PDF.",
        actions={"deep_link": "/search?mode=discover&provider=orcid"},
    ),
]


def categories_public() -> list[dict[str, str]]:
    return [{"id": cid, "name": name, "description": desc} for cid, name, desc in CATEGORIES]


def _public_row(defn: dict[str, Any]) -> dict[str, Any]:
    availability = defn["availability"]
    configured = True
    check = defn.get("server_configured_check")
    if callable(check):
        try:
            configured = bool(check())
        except Exception:
            configured = False

    # Honesty rules for the public/landing catalog:
    # - Roadmap items stay "Coming soon" (availability=soon).
    # - Live product connectors stay Live even if OAuth env is unset —
    #   missing credentials are an ops/setup issue (Settings shows server_configured).
    # - AI model providers & Google sign-in still demote when keys are absent
    #   so we don't advertise login/models the deploy cannot run.
    display_availability = availability
    if availability == "live" and defn["category"] == "ai" and not configured:
        display_availability = "soon"
        status_label = "Coming Soon"
    elif availability == "live" and defn["id"] == "google_oauth" and not configured:
        display_availability = "soon"
        status_label = "Coming Soon"
    elif display_availability == "live":
        status_label = "Live"
    elif display_availability == "soon":
        status_label = "Coming Soon"
    else:
        status_label = "Not planned"

    return {
        "id": defn["id"],
        "name": defn["name"],
        "category": defn["category"],
        "status": status_label,
        "availability": display_availability,
        "capabilities": dict(defn["capabilities"]),
        "supported_features": list(defn["supported_features"]),
        "auth": defn["auth"],
        "brand_color": defn["brand_color"],
        "logo": defn["logo"],
        "mark": defn["mark"],
        "blurb": defn.get("blurb") or "",
        "docs_url": defn.get("docs_url") or "",
        "landing": bool(defn.get("landing", True)),
        "server_configured": configured,
    }


def public_catalog() -> dict[str, Any]:
    providers = [_public_row(p) for p in PROVIDER_DEFS if p.get("landing", True)]
    return {"categories": categories_public(), "providers": providers}


def _count_imported(db, UserFile, select_fn, user_id: int, provider_id: str) -> int:
    if provider_id not in {
        "zotero",
        "mendeley",
        "bibtex",
        "ris",
        "openalex",
        "pubmed",
        "google_drive",
        "arxiv",
        "europe_pmc",
        "orcid",
        "dropbox",
        "onedrive",
    }:
        return 0
    try:
        from sqlalchemy import or_, func

        q = select_fn(func.count()).select_from(UserFile).where(UserFile.user_id == user_id)
        if provider_id in {
            "zotero",
            "mendeley",
            "pubmed",
            "google_drive",
            "arxiv",
            "europe_pmc",
            "orcid",
            "dropbox",
            "onedrive",
        }:
            q = q.where(
                or_(
                    UserFile.external_provider == provider_id,
                    UserFile.metadata_source == provider_id,
                )
            )
        else:
            q = q.where(UserFile.metadata_source == provider_id)
        return int(db.execute(q).scalar() or 0)
    except Exception:
        return 0


def _last_sync_health(db, LibrarySyncRun, select_fn, user_id: int, provider_id: str) -> dict[str, Any]:
    if LibrarySyncRun is None or provider_id not in {"zotero", "mendeley"}:
        return {"ok": True, "error": "", "last_run_status": None}
    try:
        row = (
            db.execute(
                select_fn(LibrarySyncRun)
                .where(
                    LibrarySyncRun.user_id == user_id,
                    LibrarySyncRun.provider == provider_id,
                )
                .order_by(LibrarySyncRun.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if not row:
            return {"ok": True, "error": "", "last_run_status": None}
        err = (getattr(row, "error", None) or "")[:300]
        status = getattr(row, "status", None) or ""
        return {
            "ok": status != "error",
            "error": err if status == "error" else "",
            "last_run_status": status,
        }
    except Exception:
        return {"ok": True, "error": "", "last_run_status": None}


def build_catalog(
    *,
    user_id: int | None = None,
    SessionLocal=None,
    LibraryConnection=None,
    LibrarySyncRun=None,
    UserFile=None,
    select_fn=None,
    google_connected: bool = False,
) -> dict[str, Any]:
    connected_map: dict[str, Any] = {}
    db = None
    if user_id is not None and SessionLocal and LibraryConnection and select_fn:
        db = SessionLocal()
        try:
            rows = (
                db.execute(
                    select_fn(LibraryConnection).where(
                        LibraryConnection.user_id == user_id,
                        LibraryConnection.status == "active",
                    )
                )
                .scalars()
                .all()
            )
            for r in rows:
                connected_map[r.provider] = r
        except Exception:
            connected_map = {}

    providers: list[dict[str, Any]] = []
    try:
        for defn in PROVIDER_DEFS:
            base = _public_row(defn)
            pid = defn["id"]

            if base["availability"] != "live":
                connection_state = "coming_soon"
            elif defn.get("connectable"):
                if not base.get("server_configured", True):
                    connection_state = "not_connected"
                else:
                    connection_state = "connected" if pid in connected_map else "not_connected"
            elif pid == "google_oauth":
                connection_state = "connected" if google_connected else "not_connected"
            else:
                connection_state = "n/a"

            last_sync = None
            items_imported = 0
            health = {"ok": True, "error": "", "last_run_status": None}
            username = ""

            if connection_state == "connected" and pid in connected_map:
                row = connected_map[pid]
                if row.last_synced_at:
                    last_sync = row.last_synced_at.isoformat()
                try:
                    meta = json.loads(row.meta_json or "{}")
                    username = meta.get("username") or meta.get("display_name") or ""
                except Exception:
                    username = ""

            if db is not None and UserFile and select_fn and user_id is not None:
                items_imported = _count_imported(db, UserFile, select_fn, user_id, pid)
                health = _last_sync_health(db, LibrarySyncRun, select_fn, user_id, pid)

            if connection_state == "coming_soon":
                status = "Coming Soon"
            elif connection_state == "connected":
                status = "Connected"
            elif connection_state == "not_connected":
                status = "Not Connected"
            else:
                status = "Live" if base["availability"] == "live" else base["status"]

            providers.append(
                {
                    **base,
                    "status": status,
                    "connection_state": connection_state,
                    "connection": {
                        "state": connection_state,
                        "username": username,
                        "last_sync": last_sync,
                        "items_imported": items_imported,
                    },
                    "last_sync": last_sync,
                    "health": health,
                    "actions": dict(defn.get("actions") or {}),
                    "connectable": bool(defn.get("connectable")),
                }
            )
    finally:
        if db is not None:
            db.close()

    return {"categories": categories_public(), "providers": providers}


def register_provider(defn: dict[str, Any]) -> None:
    """Append a provider (tests / future adapters)."""
    PROVIDER_DEFS.append(defn)
