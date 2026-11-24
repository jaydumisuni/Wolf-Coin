"""Android-embedded Wolf-Coin native backend. Same a10 source, signed JSON contract.

Called only from the trusted Android host WebMessage bridge. Third-party website
WebViews never receive this Python object or its owner-held HMAC key.
"""
from __future__ import annotations
import hashlib
import hmac
import json
from pathlib import Path
import secrets

from wolf_app.bridge import process, _initialize_native_key, _read_native_key
from wolf_app.store import ApplicationStore


class WolfNativeApp:
    def __init__(self, files_dir: str):
        root=Path(files_dir) / "wolf-native"
        root.mkdir(parents=True,exist_ok=True)
        self.key_path=root/"bridge.key"
        if not self.key_path.exists():
            try:
                _initialize_native_key(self.key_path)
            except FileExistsError:
                pass
        self.key=_read_native_key(self.key_path)
        self.store=ApplicationStore(root/"application.sqlite3")
        self.request("host.startup", json.dumps({
            "host_instance_id":"android_"+secrets.token_hex(16)
        }))

    def request(self, operation:str, payload_json:str) -> str:
        payload=json.loads(payload_json)
        if not isinstance(payload,dict):
            raise ValueError("Native backend payload must be a JSON object")
        envelope={
            "schema":"wolf.app.request.v1",
            "request_id":"android_"+secrets.token_hex(12),
            "operation":operation,
            "payload":payload
        }
        raw=json.dumps(envelope,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
        envelope["auth_tag"]=hmac.new(self.key,raw.encode("utf-8"),hashlib.sha256).hexdigest()
        outcome=process(self.store,json.dumps(envelope,ensure_ascii=False),key=self.key)
        return json.dumps(outcome,ensure_ascii=False,separators=(",",":"))

    def status(self) -> str:
        return self.request("bridge.capabilities","{}")
