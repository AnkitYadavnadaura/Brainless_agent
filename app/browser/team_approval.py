"""Concrete desktop-action approval with a bounded, cancellable terminal wait."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

from app.safety.redaction import redact


async def confirm_desktop_action(action, *, timeout_seconds=60, progress=print):
    """No terminal, no approval; timeout and cancellation never authorize an action."""
    progress('Desktop action requires confirmation:\n' + json.dumps(redact({
        'tool': action.action_type, 'arguments': action.arguments, 'reason': action.reason,
    }), ensure_ascii=True, indent=2, default=str))
    if not sys.stdin.isatty() or os.name != 'nt':
        progress('No interactive Windows terminal is available; action remains blocked.')
        return False
    import msvcrt
    progress(f'Type yes and Enter to approve this action ({timeout_seconds}s timeout); any other answer denies.')
    deadline = time.monotonic() + timeout_seconds
    characters = []
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            value = msvcrt.getwch()
            if value == '\x03':
                raise KeyboardInterrupt
            if value in ('\r', '\n'):
                progress('')
                return ''.join(characters).strip().casefold() == 'yes'
            if value == '\b':
                if characters:
                    characters.pop()
            elif value in ('\x00', '\xe0'):
                if msvcrt.kbhit():
                    msvcrt.getwch()
            elif value.isprintable() and len(characters) < 16:
                characters.append(value)
                msvcrt.putwch(value)
        await asyncio.sleep(.05)
    progress('Approval timed out; action remains blocked.')
    return False
