"""Wolf-Coin private, offline forward-market evidence recorder.

The CLI NEVER fetches pages, asks for passwords, or places a bet. It records
explicitly supplied source evidence bytes in immutable owner-private files.
An operator can obtain public provider evidence separately with Wolf Browser.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import argparse
import json
import re

from wolf_lab.forward_market import (
    MarketQuote, QuoteBook, QuoteRefused, canonical, frozen, immutable,
)

SCHEMA="wolf.market-capture-cli.v1"
JOURNAL=re.compile(r"journal-([0-9]{6})\.json")


def _private(path:Path):
    target=path.resolve()
    if not target.is_dir() or target.stat().st_mode & 0o077:
        raise QuoteRefused("owner-private evidence directory required")
    return target


def _journal_path(directory:Path):
    paths=[]
    for p in directory.glob("journal-*.json"):
        match=JOURNAL.fullmatch(p.name)
        if not match:
            raise QuoteRefused("unexpected journal filename")
        paths.append((int(match.group(1)),p))
    paths.sort()
    if paths and [x[0] for x in paths]!=list(range(1,len(paths)+1)):
        raise QuoteRefused("immutable journal numbering gap")
    return paths


def _state(source:dict,directory:Path)->QuoteBook:
    entries=_journal_path(directory)
    if not entries:
        return QuoteBook(source)
    latest=json.loads(entries[-1][1].read_bytes())
    return QuoteBook.replay(source,latest,directory)


def ingest(source_path:Path,directory:Path,quote_path:Path,raw_path:Path,
           schedule_path:Path|None=None)->dict:
    source=frozen(source_path)
    evidence=_private(directory)
    raw=raw_path.read_bytes()
    schedule=schedule_path.read_bytes() if schedule_path else None
    quote=MarketQuote(**json.loads(quote_path.read_bytes()))
    existing=_state(source,evidence)
    previous=len(existing.records)
    item=existing.record(quote,raw,schedule_raw=schedule)
    if len(existing.records)==previous:
        return {"status":"IDEMPOTENT_EXISTING_CAPTURE","capture_id":quote.capture_id,
                "quotes_recorded":previous,"financial_authority":False}
    raw_file=evidence/(quote.evidence_sha256+".json")
    if not raw_file.exists():
        immutable(raw_file,raw)
    elif raw_file.read_bytes()!=raw:
        raise QuoteRefused("evidence name exists with different bytes")
    if schedule is not None:
        schedule_file=evidence/(quote.schedule_evidence_sha256+".json")
        if not schedule_file.exists():
            immutable(schedule_file,schedule)
        elif schedule_file.read_bytes()!=schedule:
            raise QuoteRefused("schedule evidence digest collision")
    target=evidence/("journal-%06d.json"%len(existing.records))
    checksum=immutable(target,canonical(existing.snapshot()))
    return {"status":"PROVISIONAL_MARKET_CAPTURED",
            "capture_id":quote.capture_id,
            "quotes_recorded":len(existing.records),
            "schedule_changed":item["schedule_changed"],
            "independent_price_authentication":False,
            "financial_authority":False,
            "journal_sha256":checksum}


def verify(source_path:Path,directory:Path)->dict:
    obj=_state(frozen(source_path),_private(directory))
    return {"status":"SEALED_MARKET_JOURNAL_VERIFIED",
            "quotes_recorded":len(obj.records),
            "source_forecast_digest":obj.snapshot()["original_forecast_digest_sha256"],
            "independent_market_source_authenticated":False,
            "live_execution_allowed":False}


def probe(file:Path)->dict:
    raw=file.read_bytes()
    if len(raw)>1024*1024:
        raise QuoteRefused("source probe outside bounds")
    text=raw[:200].strip().lower()
    html=(text.startswith(b"<html") or text.startswith(b"<!doctype html")
          or b"<html" in text)
    if html:
        status="REJECT_HTML_NOT_MARKET_CSV"
    else:
        try:
            import csv
            data=raw.decode("utf-8-sig")
            reader=csv.DictReader(data.splitlines())
            headers=reader.fieldnames or []
            status=("CSV_SCHEMA_INSPECTION_REQUIRED" if len(headers)>=5 else
                    "REJECT_UNRECOGNIZED_QUOTE_SOURCE")
        except (UnicodeError,csv.Error):
            status="REJECT_UNRECOGNIZED_QUOTE_SOURCE"
    return {"status":status,
            "sha256":sha256(raw).hexdigest(),
            "bytes":len(raw),"not_provider_authenticated":True}


def main(argv=None):
    parser=argparse.ArgumentParser(prog="wolf-forward-market")
    cmd=parser.add_subparsers(dest="command",required=True)
    common=argparse.ArgumentParser(add_help=False)
    common.add_argument("--freeze",required=True,type=Path)
    common.add_argument("--evidence-dir",required=True,type=Path)
    cap=cmd.add_parser("capture",parents=[common])
    cap.add_argument("--quote",required=True,type=Path)
    cap.add_argument("--source-evidence",required=True,type=Path)
    cap.add_argument("--schedule-evidence",type=Path)
    cmd.add_parser("verify",parents=[common])
    pro=cmd.add_parser("probe")
    pro.add_argument("--raw",required=True,type=Path)
    a=parser.parse_args(argv)
    try:
        if a.command=="probe":
            result=probe(a.raw)
        elif a.command=="verify":
            result=verify(a.freeze,a.evidence_dir)
        else:
            result=ingest(a.freeze,a.evidence_dir,a.quote,a.source_evidence,a.schedule_evidence)
        print(json.dumps({"schema":SCHEMA,**result},sort_keys=True))
    except (QuoteRefused,ValueError,KeyError,OSError,UnicodeError) as e:
        parser.exit(2,"MARKET_CAPTURE_REFUSED: "+str(e)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
