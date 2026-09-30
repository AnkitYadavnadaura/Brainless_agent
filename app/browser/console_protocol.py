"""Nonce-bound console receipts, independent of asynchronous DevTools helper scope."""
from __future__ import annotations

import json
import re

RESULT_PREFIX = "BRAINLESS_RESULT:"


def wrap_console_expression(script: str, nonce: str) -> str:
    """Capture copy synchronously and execute the expression exactly once."""
    if not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("A console receipt requires a fresh nonce")
    return (
        "((__fleet_copy)=>{const __fleet_nonce=" + json.dumps(nonce) + ";"
        "const __fleet_steps=[];"
        "const __fleet_step=(stage)=>{const s=String(stage).slice(0,120);"
        "if(__fleet_steps.length<80)__fleet_steps.push(s);"
        "console.log('[Brainless '+__fleet_nonce+'] '+s);};"
        "const __fleet_publish=(receipt)=>{"
        "receipt.steps=__fleet_steps.slice();const raw=JSON.stringify(receipt);"
        "console.log('BRAINLESS_RESULT:'+__fleet_nonce+':'+raw);"
        "if(__fleet_copy){try{__fleet_copy(raw);}catch(e){__fleet_step('receipt.clipboard_failed');}}"
        "else __fleet_step('receipt.console_only');};"
        "return (async()=>{try{__fleet_step('execution.started');const value=await (" + script + ");"
        "__fleet_step('execution.completed');"
        "__fleet_publish({brainless_nonce:__fleet_nonce,ok:true,value});}"
        "catch(error){__fleet_step('execution.failed');"
        "__fleet_publish({brainless_nonce:__fleet_nonce,ok:false,error:String(error)});}})();"
        "})(typeof copy==='function'?copy:null);"
    )


def parse_console_receipt(raw: str, nonce: str) -> dict | None:
    """Accept only a complete receipt for this invocation, not a page's stray log."""
    if not isinstance(raw, str) or len(raw) > 2_000_000:
        return None
    prefix = RESULT_PREFIX + nonce + ":"
    if raw.startswith(prefix):
        raw = raw[len(prefix):]
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(value, dict) and value.get("brainless_nonce") == nonce:
        return value
    return None
