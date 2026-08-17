#!/usr/bin/env python3
"""Daily rollup of Caddy access logs — who actually visited, and who only said so.

    .venv/bin/python -m tools.caddy_rollup              # yesterday, write
    .venv/bin/python -m tools.caddy_rollup --dry-run    # print, write nothing
    .venv/bin/python -m tools.caddy_rollup --date 2026-08-15

Feeds the sysadmin pass. Emits DATA, never prose — the agent decides what is
worth saying.

Three things this exists to get right, all learned the hard way (2026-08-16):

1. NEVER `client_ip`. Caddy sits behind Cloudflare with no `trusted_proxies`,
   so `client_ip` and `remote_ip` are Cloudflare edge addresses on every single
   line. The real visitor is in the `Cf-Connecting-Ip` header, with country in
   `Cf-Ipcountry`. Reading the header works before and after that config is
   fixed, so this does not depend on it.

2. NEVER report a user-agent as fact. 621 requests claimed to be GPTBot; 582
   came from two Google Cloud VMs probing for `/.env` and `/.git/config`. A
   collector that counted UA strings would put a fabrication in the brief every
   morning. Crawlers are forward-confirmed by reverse DNS, and `verified` is
   reported separately from `claimed`. The gap between them is a security
   signal in its own right.

3. An empty rollup is an ERROR, not a zero. "No traffic" and "the parser broke"
   look identical in a JSON file and mean opposite things, so parsing nothing
   exits non-zero and the timer's OnFailure pages.

Visitor IPs are retained (operator decision 2026-08-16: access logs are
ordinary, Cloudflare already holds every one of these, and repeat-visitor
detection is the question worth answering once the publishing drip starts).
State lives under `pipelines/sysadmin/state/`, which is gitignored — this repo
is public and a push is a publish.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import socket
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_DIR = Path("/var/log/caddy")
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "pipelines" / "sysadmin" / "state" / "caddy"
CACHE = STATE / "verified-ips.json"
RETAIN_DAYS = 90
DNS_TIMEOUT = 3.0

# Suffix → label. Forward-confirmed: PTR must end with the suffix AND the
# forward lookup of that hostname must return the original IP.
CRAWLER_DOMAINS = {
    ".googlebot.com": "Googlebot",
    ".google.com": "Google",
    ".search.msn.com": "Bingbot",
    ".crawl.yahoo.net": "Slurp",
    ".yandex.com": "YandexBot",
    ".yandex.ru": "YandexBot",
    ".baidu.com": "Baiduspider",
    ".applebot.apple.com": "Applebot",
    ".duckduckgo.com": "DuckDuckBot",
}

# Crawlers whose identity CAN be settled by reverse DNS. The others — GPTBot,
# ClaudeBot, PerplexityBot, Amazonbot — publish IP ranges instead and have no
# PTR to confirm, so "unverified" for them means "not checkable by this method",
# NOT "forged". Conflating the two would report honest crawlers as liars.
RDNS_VERIFIABLE = {"Googlebot", "bingbot", "Slurp", "DuckDuckBot",
                   "YandexBot", "Baiduspider", "Applebot"}

# Reverse DNS cannot CONFIRM a range-published crawler, but it can DISCONFIRM
# one. No first-party crawler runs from a rented consumer VM, so a GPTBot claim
# whose PTR lands on googleusercontent.com is provably not OpenAI. This is what
# exposed the scanner farm on 2026-08-16 — 582 "GPTBot" requests from two GCE
# boxes, every URI a 404 hunting for secrets.
CLOUD_HOSTS = (".googleusercontent.com", ".compute.amazonaws.com", ".amazonaws.com",
               ".digitalocean.com", ".vultr.com", ".linode.com", ".hetzner.de",
               ".contaboserver.net", ".ovh.net", ".azure.com", ".oracle.com")

# What a UA *claims*. Never trusted; used only to decide who is worth verifying
# and to compute the forgery gap.
CLAIMS = re.compile(
    r"(Googlebot|bingbot|Slurp|DuckDuckBot|YandexBot|Baiduspider|Applebot|"
    r"GPTBot|ClaudeBot|Claude-|CCBot|Amazonbot|Bytespider|PerplexityBot|"
    r"meta-external|Google-Extended|AhrefsBot|SemrushBot|facebookexternalhit|"
    r"Twitterbot|LinkedInBot|Slackbot|Discordbot)", re.I)

# Known probe shapes. A 404 matching these is weather, not signal. Everything
# else lands in `suspect_404` for a human to glance at — note this does NOT
# claim to detect broken links: Caddy does not log Referer here, so there is no
# way to tell an internal broken link from an external one. It surfaces
# candidates; it does not diagnose.
SCANNER = re.compile(
    r"(\.env|\.git|\.aws|\.ssh|/wp-|/wordpress|/xmlrpc|/actuator|/cgi-bin|"
    r"\.php$|/vendor/|/config\.json|/telescope|/phpmyadmin|/solr|/druid|"
    r"/_ignition|/api/env|/server-status|\.well-known/security)", re.I)

# Our own tooling hitting the Ghost Admin API. A 404 here is an idempotency
# probe ("does this slug exist yet?"), not a broken link, and it would other-
# wise fill the suspect bucket every time anyone runs ghost_upsert.
OPERATOR = re.compile(r"^/ghost/api/", re.I)


def load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def ptr(ip: str) -> str | None:
    socket.setdefaulttimeout(DNS_TIMEOUT)
    try:
        return socket.gethostbyaddr(ip)[0].lower().rstrip(".")
    except (OSError, socket.herror):
        return None


def disconfirmed(ip: str) -> bool:
    """True when the PTR proves the claim false — a rented VM wearing a name."""
    h = ptr(ip)
    return bool(h and h.endswith(CLOUD_HOSTS))


def verify(ip: str, cache: dict) -> str | None:
    """Forward-confirmed reverse DNS. Returns a crawler label, or None.

    Cached across runs — crawler ranges are stable and this keeps steady-state
    lookups near zero. Only IPs that resolve to a crawler are cached; a failed
    lookup is not stored, so a transient DNS failure never becomes permanent.
    """
    if ip in cache:
        return cache[ip] or None
    socket.setdefaulttimeout(DNS_TIMEOUT)
    try:
        host = socket.gethostbyaddr(ip)[0].lower().rstrip(".")
    except (OSError, socket.herror):
        return None
    label = next((v for k, v in CRAWLER_DOMAINS.items() if host.endswith(k)), None)
    if not label:
        return None
    try:
        _, _, forward = socket.gethostbyname_ex(host)
    except OSError:
        return None
    if ip not in forward:          # PTR claims a crawler the forward record denies
        return None
    cache[ip] = label
    return label


def read_log(path: Path, start: datetime, end: datetime):
    """Yield entries in [start, end). Falls back to the newest rotated archive
    when the live file does not reach back far enough — rotation here is
    size-based, so a busy day can rotate mid-window and silently eat half of it.
    """
    files = [path]
    try:
        with path.open(errors="replace") as fh:
            first = json.loads(fh.readline() or "{}").get("ts", 0)
        if first > start.timestamp():
            archives = sorted(LOG_DIR.glob(f"{path.stem}-*.log.gz"))
            if archives:
                files.insert(0, archives[-1])
    except (OSError, json.JSONDecodeError):
        pass

    for f in files:
        opener = gzip.open if f.suffix == ".gz" else open
        try:
            with opener(f, "rt", errors="replace") as fh:
                for line in fh:
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = e.get("ts", 0)
                    if start.timestamp() <= ts < end.timestamp():
                        yield e
        except OSError:
            continue


def rollup(day: datetime, cache: dict) -> dict:
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    out = {"date": start.date().isoformat(), "hosts": {}, "totals": {}}
    grand = Counter()
    seen_ips: dict[str, Counter] = defaultdict(Counter)

    for path in sorted(LOG_DIR.glob("*.log")):
        host = path.stem
        n = 0
        status, country, claimed, verified = Counter(), Counter(), Counter(), Counter()
        suspect, scanner_hits, ips = Counter(), 0, Counter()
        operator_hits, unverifiable, disconf = 0, Counter(), Counter()

        for e in read_log(path, start, end):
            n += 1
            req = e.get("request", {})
            h = req.get("headers", {})
            ip = (h.get("Cf-Connecting-Ip") or [""])[0]
            ua = (h.get("User-Agent") or [""])[0]
            uri, st = req.get("uri", ""), e.get("status")

            status[str(st)] += 1
            country[(h.get("Cf-Ipcountry") or ["?"])[0]] += 1
            if ip:
                ips[ip] += 1

            m = CLAIMS.search(ua)
            if m:
                claim = m.group(1)
                claimed[claim] += 1
                if claim not in RDNS_VERIFIABLE:
                    if ip and disconfirmed(ip):
                        disconf[claim] += 1
                    else:
                        unverifiable[claim] += 1
                elif ip and (label := verify(ip, cache)):
                    verified[label] += 1
            elif ip:
                seen_ips[host][ip] += 1      # non-bot traffic, for repeat visitors

            if st == 404:
                if OPERATOR.search(uri):
                    operator_hits += 1
                elif SCANNER.search(uri):
                    scanner_hits += 1
                else:
                    suspect[uri[:120]] += 1

        if not n:
            continue
        grand["requests"] += n
        out["hosts"][host] = {
            "requests": n,
            "status": dict(status.most_common()),
            "countries": dict(country.most_common(12)),
            "crawlers_claimed": dict(claimed.most_common()),
            "crawlers_verified": dict(verified.most_common()),
            "scanner_404s": scanner_hits,
            "operator_404s": operator_hits,
            "crawlers_unverifiable": dict(unverifiable.most_common()),
            "crawlers_disconfirmed": dict(disconf.most_common()),
            "suspect_404s": dict(suspect.most_common(10)),
            "unique_ips": len(ips),
            "top_human_ips": dict(seen_ips[host].most_common(10)),
        }
        grand["verified"] += sum(verified.values())
        grand["claimed"] += sum(claimed.values())
        grand["checkable"] += sum(v for k, v in claimed.items() if k in RDNS_VERIFIABLE)
        grand["unverifiable"] += sum(unverifiable.values())
        grand["disconfirmed"] += sum(disconf.values())

    out["totals"] = {
        "requests": grand["requests"],
        "crawler_claimed": grand["claimed"],
        "crawler_verified": grand["verified"],
        "crawler_unverifiable": grand["unverifiable"],
        # Claims the PTR proves false. Not an SEO number — this is somebody
        # wearing a crawler's name from a rented box, and it belongs in the
        # security half of the brief.
        "crawler_disconfirmed": grand["disconfirmed"],
        # Of the claims reverse DNS CAN settle, how many proved out. Anything
        # below 1.0 means somebody is wearing a crawler's name — a security
        # signal, not an SEO one. Claims from range-published crawlers are
        # excluded from the denominator rather than counted as failures.
        "verification_rate": round(grand["verified"] / grand["checkable"], 3)
        if grand["checkable"] else None,
    }
    return out


def prune() -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETAIN_DAYS)).date().isoformat()
    gone = 0
    for f in STATE.glob("20*.json"):
        if f.stem < cutoff:
            f.unlink()
            gone += 1
    return gone


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="YYYY-MM-DD (default: yesterday)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    day = (datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)
           if args.date else datetime.now(timezone.utc) - timedelta(days=1))

    if not LOG_DIR.is_dir():
        print(f"no log directory at {LOG_DIR}", file=sys.stderr)
        return 1

    cache = load_cache()
    data = rollup(day, cache)

    if not data["totals"]["requests"]:
        print(f"parsed 0 requests for {data['date']} — treating as failure, not "
              f"as a quiet day. Check {LOG_DIR} and the log format.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(data, indent=2))
        return 0

    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{data['date']}.json").write_text(json.dumps(data, indent=2) + "\n")
    CACHE.write_text(json.dumps(cache, indent=2) + "\n")
    t = data["totals"]
    print(f"{data['date']}: {t['requests']:,} requests across {len(data['hosts'])} hosts; "
          f"crawlers {t['crawler_verified']} verified / {t['crawler_claimed']} claimed "
          f"(rate {t['verification_rate']}); pruned {prune()} old rollups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
