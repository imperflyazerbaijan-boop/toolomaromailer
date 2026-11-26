"""Pull consented contact records from explicitly authorized JSON APIs."""
import json
import logging
import os
import random
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode, parse_qsl, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import main

LOG = logging.getLogger("toolomaro")
MAX_BODY = 5 * 1024 * 1024

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def read_config(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("sources.json must be a list")
    seen, out = set(), []
    for src in data:
        try:
            if src.get("enabled") is not True:
                continue
            name, country, url = src["id"], src["country"], src["url"]
            u = urlsplit(url)
            if (not isinstance(name,str) or not name or name in seen or
                country not in main.COUNTRIES or u.scheme != "https" or
                not u.hostname or u.username or u.password or u.fragment or
                not str(src.get("authorization_reference","")).strip()):
                raise ValueError("Invalid source")
            interval = max(60, int(src.get("interval_seconds",300)))
            delay = max(1, int(src.get("page_delay_seconds",2)))
            out.append(dict(src, interval_seconds=interval,page_delay_seconds=delay))
            seen.add(name)
        except (KeyError, ValueError, TypeError, AttributeError):
            LOG.warning("Invalid source entry skipped")
    return out

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS source_state(
        id TEXT PRIMARY KEY, cursor TEXT, next_at REAL NOT NULL DEFAULT 0,
        failures INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending',
        records INTEGER NOT NULL DEFAULT 0)""")
    db.execute("CREATE TABLE IF NOT EXISTS host_state(host TEXT PRIMARY KEY, next_at REAL NOT NULL)")
    db.commit()

def fetch(src,cursor):
    u = urlsplit(src["url"])
    params = [(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k!="cursor"]
    if cursor is not None:
        params.append(("cursor",cursor))
    url = urlunsplit((u.scheme,u.netloc,u.path,urlencode(params),""))
    headers = {"Accept":"application/json","User-Agent":"ToolomaroMailer/0.2 authorized-sync"}
    env = src.get("token_env")
    if env:
        token = os.environ.get(env)
        if not token:
            raise PermissionError("Missing API credential")
        headers["Authorization"] = "Bearer "+token
    with build_opener(NoRedirect()).open(Request(url,headers=headers),timeout=15) as resp:
        body = resp.read(MAX_BODY+1)
        if len(body)>MAX_BODY:
            raise ValueError("API response too large")
    return json.loads(body)

def retry_after(value):
    if not value:
        return 0
    try:
        return max(0,int(value))
    except ValueError:
        try:
            d = parsedate_to_datetime(value)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return max(0,(d-datetime.now(timezone.utc)).total_seconds())
        except (ValueError,TypeError,OverflowError):
            return 0

def failure(exc,attempt):
    delay = min(3600, 10 * 2 ** min(attempt,8)) + random.uniform(0,5)
    if isinstance(exc,HTTPError):
        if exc.code in (401,403):
            return "access_denied", 86400
        if exc.code == 429:
            return "rate_limited", max(delay,retry_after(exc.headers.get("Retry-After") if exc.headers else None))
        if exc.code in (400,404,410) or 300<=exc.code<400:
            return "configuration_error", 3600
    if isinstance(exc,PermissionError):
        return "credential_missing", 3600
    return "retry", delay

def parse_page(src,payload,cursor):
    if not isinstance(payload,dict) or not isinstance(payload.get("records"),list):
        raise ValueError("Invalid API page")
    nxt = payload.get("next_cursor")
    if nxt is not None and (not isinstance(nxt,str) or not nxt or len(nxt)>4096 or nxt==cursor):
        raise ValueError("Invalid or repeated cursor")
    rows = []
    for record in payload["records"]:
        if not isinstance(record,dict):
            continue
        email,evidence = record.get("email"),record.get("consent_evidence")
        if (record.get("consent") is not True or not isinstance(email,str) or
            not isinstance(evidence,str) or not email.strip() or not evidence.strip() or
            record.get("country",src["country"]) != src["country"]):
            continue
        rows.append((email.strip(),src["country"],evidence.strip()))
    return rows,nxt

def sync(db,sources,fetcher=fetch):
    """At most one page per due source per tick; checkpoint with record insertion."""
    import hashlib
    init(db)
    candidates=[]
    now=time.time()
    for src in sources:
        with db:
            db.execute("INSERT OR IGNORE INTO source_state(id) VALUES(?)",(src["id"],))
        cursor,at,attempt=db.execute("SELECT cursor,next_at,failures FROM source_state WHERE id=?",(src["id"],)).fetchone()
        host=urlsplit(src["url"]).hostname if "url" in src else src["id"]
        cooldown=db.execute("SELECT next_at FROM host_state WHERE host=?",(host,)).fetchone()
        if at<=now and (not cooldown or cooldown[0]<=now):
            candidates.append((at,src["id"],host,src,cursor,attempt))
    due=[]
    used=set()
    for _,_,host,src,cursor,attempt in sorted(candidates,key=lambda r:(r[0],r[1])):
        if host not in used:
            due.append((src,cursor,attempt,host))
            used.add(host)
    with ThreadPoolExecutor(max_workers=min(40,max(1,len(due)))) as pool:
        futures={pool.submit(fetcher,src,cursor):(src,cursor,attempt,host) for src,cursor,attempt,host in due}
        for f in as_completed(futures):
            src,cursor,attempt,host=futures[f]
            try:
                rows,nxt=parse_page(src,f.result(),cursor)
            except Exception as exc:
                status,delay=failure(exc,attempt)
                with db:
                    db.execute("UPDATE source_state SET status=?,next_at=?,failures=failures+1 WHERE id=?",
                               (status,time.time()+delay,src["id"]))
                    if status=="rate_limited":
                        db.execute("INSERT INTO host_state VALUES(?,?) ON CONFLICT(host) DO UPDATE SET next_at=max(next_at,excluded.next_at)",(host,time.time()+delay))
                continue
            with db:
                for email,country,evidence in rows:
                    key=hashlib.sha256((email.casefold()+"\0"+country).encode()).hexdigest()
                    db.execute("INSERT OR IGNORE INTO queue(id,email,country,evidence) VALUES(?,?,?,?)",
                               (key,email,country,evidence))
                db.execute("""UPDATE source_state SET cursor=?,next_at=?,failures=0,
                    status=?,records=records+? WHERE id=?""",
                    (nxt,time.time()+(src["page_delay_seconds"] if nxt else src["interval_seconds"]),
                     "paging" if nxt else "complete",len(rows),src["id"]))
    return len(due)
