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
    _transport_proof,digest,
)
from dataclasses import replace

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
    ledger=QuoteBook.replay(source,latest,directory)
    if len(ledger.records)!=len(entries):
        raise QuoteRefused("journal version and record count differ")
    # Each immutable version must be the exact prefix of the replayed ledger.
    for number,path in entries:
        prior=json.loads(path.read_bytes())
        expected=dict(latest)
        expected["records"]=ledger.records[:number]
        expected["last_sha256"]=ledger.records[number-1]["sha256"]
        expected.pop("seal_sha256")
        expected["seal_sha256"]=digest(expected)
        if prior!=expected:
            raise QuoteRefused("immutable journal history differs from replayed prefix")
    return ledger


def ingest(source_path:Path,directory:Path,quote_path:Path,raw_path:Path,
           schedule_path:Path|None=None,transport_path:Path|None=None)->dict:
    source=frozen(source_path)
    evidence=_private(directory)
    raw=raw_path.read_bytes()
    schedule=schedule_path.read_bytes() if schedule_path else None
    transport=transport_path.read_bytes() if transport_path else None
    quote=MarketQuote(**json.loads(quote_path.read_bytes()))
    existing=_state(source,evidence)
    previous=len(existing.records)
    item=existing.record(quote,raw,schedule_raw=schedule,transport_raw=transport)
    if len(existing.records)==previous:
        return {"status":"IDEMPOTENT_EXISTING_CAPTURE","capture_id":quote.capture_id,
                "quotes_recorded":previous,"financial_authority":False}
    ext=".html" if quote.evidence_kind=="public_1x2_html" else ".json"
    raw_file=evidence/(quote.evidence_sha256+ext)
    if not raw_file.exists():
        immutable(raw_file,raw)
    elif raw_file.read_bytes()!=raw:
        raise QuoteRefused("evidence name exists with different bytes")
    if schedule is not None:
        schedule_file=evidence/(quote.schedule_evidence_sha256+ext)
        if not schedule_file.exists():
            immutable(schedule_file,schedule)
        elif schedule_file.read_bytes()!=schedule:
            raise QuoteRefused("schedule evidence digest collision")
    if transport is not None:
        headers=evidence/(quote.transport_evidence_sha256+".headers")
        if not headers.exists():
            immutable(headers,transport)
        elif headers.read_bytes()!=transport:
            raise QuoteRefused("transport evidence file collision")
    target=evidence/("journal-%06d.json"%len(existing.records))
    checksum=immutable(target,canonical(existing.snapshot()))
    return {"status":"PROVISIONAL_MARKET_CAPTURED",
            "capture_id":quote.capture_id,
            "quotes_recorded":len(existing.records),
            "schedule_changed":item["schedule_changed"],
            "independent_price_authentication":False,
            "financial_authority":False,
            "journal_sha256":checksum}


def attest(source_path:Path,directory:Path,capture_id:str,headers_path:Path)->dict:
    """Append a separate immutable HTTP-date proof without rewriting a quote."""
    source=frozen(source_path)
    evidence=_private(directory)
    ledger=_state(source,evidence)
    if capture_id not in ledger.by_id:
        raise QuoteRefused("unknown quote capture ID")
    recorded=ledger.by_id[capture_id]["quote"]
    quote=MarketQuote(**recorded)
    headers=headers_path.read_bytes()
    hashed=sha256(headers).hexdigest()
    if quote.transport_evidence_sha256 is not None:
        raise QuoteRefused("quote already contains HTTP transport proof")
    typed=replace(quote,transport_evidence_sha256=hashed)
    _transport_proof(headers,typed)
    meta={
       "schema":"wolf.quote-transport-date-attestation.v1",
       "capture_id":capture_id,
       "quote_sha256":digest(recorded),
       "http_headers_sha256":hashed,
       "source_observed_utc":typed.observed_utc,
       "journal_tail_sha256":ledger.tail,
       "financial_authority":False,
       "independent_provider_authentication":False}
    meta["seal_sha256"]=digest(meta)
    filename="attestation-"+sha256(capture_id.encode()).hexdigest()+".json"
    attestation=evidence/filename
    if attestation.exists():
        if attestation.read_bytes()!=canonical(meta):
            raise QuoteRefused("existing transport attestation differs")
    else:
        transport=evidence/(hashed+".headers")
        if transport.exists():
            if transport.read_bytes()!=headers:
                raise QuoteRefused("transport file name collision")
        else:
            immutable(transport,headers)
        immutable(attestation,canonical(meta))
    return {"status":"LOCAL_HTTP_DATE_PROOF_RECORDED",
            "capture_id":capture_id,"http_header_sha256":hashed,
            "provider_origin_cryptographically_authenticated":False,
            "financial_authority":False}


def _transport_attestations(directory:Path,ledger:QuoteBook)->int:
    count=0
    for entry in directory.glob("attestation-*.json"):
        meta=json.loads(entry.read_bytes())
        copy=dict(meta)
        seal=copy.pop("seal_sha256",None)
        if seal!=digest(copy) or copy.get("schema")!="wolf.quote-transport-date-attestation.v1":
            raise QuoteRefused("transport attestation seal mismatch")
        capture_id=copy.get("capture_id")
        if entry.name!="attestation-"+sha256(str(capture_id).encode()).hexdigest()+".json":
            raise QuoteRefused("transport attestation filename mismatch")
        record=ledger.by_id.get(capture_id)
        if record is None or digest(record["quote"])!=copy.get("quote_sha256"):
            raise QuoteRefused("transport attestation unbound quote")
        sequence=next(e["sequence"] for e in ledger.records if e["record"]["quote"]["capture_id"]==capture_id)
        valid_tails={e["sha256"] for e in ledger.records[sequence-1:]}
        if copy.get("journal_tail_sha256") not in valid_tails:
            raise QuoteRefused("transport attestation journal tail is not a valid later prefix")
        if record["quote"]["observed_utc"]!=copy.get("source_observed_utc"):
            raise QuoteRefused("transport time contradicts quote")
        headers=(directory/(copy["http_headers_sha256"]+".headers")).read_bytes()
        quote=MarketQuote(**record["quote"])
        _transport_proof(headers,replace(quote,transport_evidence_sha256=copy["http_headers_sha256"]))
        count+=1
    return count


def verify(source_path:Path,directory:Path)->dict:
    obj=_state(frozen(source_path),_private(directory))
    attestations=_transport_attestations(directory,obj)
    return {"status":"SEALED_MARKET_JOURNAL_VERIFIED",
            "quotes_recorded":len(obj.records),
            "http_server_date_attestations_checked":attestations,
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
    cap.add_argument("--http-headers",type=Path)
    cmd.add_parser("verify",parents=[common])
    att=cmd.add_parser("attest",parents=[common])
    att.add_argument("--capture-id",required=True)
    att.add_argument("--http-headers",required=True,type=Path)
    pro=cmd.add_parser("probe")
    pro.add_argument("--raw",required=True,type=Path)
    a=parser.parse_args(argv)
    try:
        if a.command=="probe":
            result=probe(a.raw)
        elif a.command=="verify":
            result=verify(a.freeze,a.evidence_dir)
        elif a.command=="attest":
            result=attest(a.freeze,a.evidence_dir,a.capture_id,a.http_headers)
        else:
            result=ingest(a.freeze,a.evidence_dir,a.quote,a.source_evidence,a.schedule_evidence,a.http_headers)
        print(json.dumps({"schema":SCHEMA,**result},sort_keys=True))
    except (QuoteRefused,ValueError,KeyError,OSError,UnicodeError) as e:
        parser.exit(2,"MARKET_CAPTURE_REFUSED: "+str(e)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
