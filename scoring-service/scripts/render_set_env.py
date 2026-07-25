"""Set an env var on a Render service and trigger a cache-clearing deploy.

Fixes the standing Phase-0 gap: the hosted dashboard needs
SCORING_SERVICE_URL baked in at BUILD time (Next.js resolves rewrites during
`next build`, not at runtime), so setting the var is not enough on its own — it
must be followed by a deploy with the build cache cleared.

Secret handling (vault rule 8): the Render API key comes ONLY from the env var
SHINEHACKATHON_RENDER_API_KEY. It is never written to disk, logged, or echoed.

Usage (PowerShell):
    $env:SHINEHACKATHON_RENDER_API_KEY = "rnd_xxx"          # you drop this in
    C:\\Users\\lucas\\anaconda3\\python.exe scripts/render_set_env.py

Defaults set SCORING_SERVICE_URL on the dashboard service. Override via flags:
    python scripts/render_set_env.py \
        --service triage-dashboard \
        --key SCORING_SERVICE_URL \
        --value https://triage-scoring-service.onrender.com \
        --clear-cache            # omit --no-deploy to also deploy

Render API: https://render.com/docs/api  (Bearer auth, /v1).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.render.com/v1"

# Defaults for THIS project's standing fix. The value has NO trailing slash —
# next.config.mjs appends the path (`${SCORING_SERVICE}/caseload`); a trailing
# slash would produce `//caseload` and 404 the proxy.
DEFAULT_SERVICE = "triage-dashboard"
DEFAULT_KEY = "SCORING_SERVICE_URL"
DEFAULT_VALUE = "https://triage-scoring-service.onrender.com"


def _req(method: str, path: str, token: str, body: dict | None = None) -> object:
    """One authenticated Render API call. Raises RuntimeError with the server's
    message on non-2xx so failures are legible (bad key, unknown service, ...)."""
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"{method} {path} -> network error: {e.reason}") from None


def find_service(token: str, name: str) -> dict:
    """Resolve a service by (case-insensitive substring) name. Render wraps each
    list item as {\"service\": {...}}; we unwrap and match on the real name so
    'triage-dashboard' finds 'triage-dashboard-zyur'."""
    q = urllib.parse.urlencode({"limit": 100})
    items = _req("GET", f"/services?{q}", token)
    matches = []
    for it in items if isinstance(items, list) else []:
        svc = it.get("service", it) if isinstance(it, dict) else {}
        if name.lower() in str(svc.get("name", "")).lower():
            matches.append(svc)
    if not matches:
        names = [ (it.get("service", it) or {}).get("name") for it in items ] \
            if isinstance(items, list) else []
        raise SystemExit(f"no service matching '{name}'. Found: {names}")
    if len(matches) > 1:
        raise SystemExit(
            f"'{name}' is ambiguous: {[m.get('name') for m in matches]}. "
            "Pass the exact --service name."
        )
    return matches[0]


def set_env_var(token: str, service_id: str, key: str, value: str) -> None:
    """Upsert ONE env var (PUT single-key endpoint leaves the others intact —
    unlike the bulk PUT, which replaces the whole set)."""
    _req("PUT", f"/services/{service_id}/env-vars/{key}", token, {"value": value})


def deploy(token: str, service_id: str, clear_cache: bool) -> dict:
    body = {"clearCache": "clear" if clear_cache else "do_not_clear"}
    return _req("POST", f"/services/{service_id}/deploys", token, body)  # type: ignore[return-value]


def main() -> None:
    ap = argparse.ArgumentParser(description="Set a Render env var + deploy.")
    ap.add_argument("--service", default=DEFAULT_SERVICE)
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--value", default=DEFAULT_VALUE)
    ap.add_argument("--no-deploy", action="store_true",
                    help="set the var only; skip the deploy")
    ap.add_argument("--no-clear-cache", action="store_true",
                    help="deploy WITHOUT clearing the build cache (not recommended "
                         "for Next rewrite changes)")
    args = ap.parse_args()

    token = os.environ.get("SHINEHACKATHON_RENDER_API_KEY")
    if not token:
        raise SystemExit(
            "SHINEHACKATHON_RENDER_API_KEY is not set. In PowerShell:\n"
            '  $env:SHINEHACKATHON_RENDER_API_KEY = "rnd_xxx"'
        )
    if args.value.endswith("/"):
        print(f"! stripping trailing slash from value ({args.value!r})", file=sys.stderr)
        args.value = args.value.rstrip("/")

    svc = find_service(token, args.service)
    sid, sname = svc["id"], svc.get("name")
    print(f"service: {sname} ({sid})")

    set_env_var(token, sid, args.key, args.value)
    print(f"set env: {args.key} = {args.value}")

    if args.no_deploy:
        print("skipped deploy (--no-deploy). Remember: Next bakes rewrites at "
              "BUILD time, so the var only takes effect after a clear-cache deploy.")
        return

    dep = deploy(token, sid, clear_cache=not args.no_clear_cache)
    did = dep.get("id") if isinstance(dep, dict) else None
    cache = "cache CLEARED" if not args.no_clear_cache else "cache kept"
    print(f"triggered deploy {did} ({cache})")
    print(f"watch: https://dashboard.render.com/  ->  {sname}  ->  Events")


if __name__ == "__main__":
    main()
