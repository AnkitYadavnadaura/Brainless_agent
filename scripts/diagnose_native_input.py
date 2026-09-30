"""Inspect fresh fleet composer hit tests without typing or sending a prompt."""
import asyncio
import argparse
import json
import uuid
from pathlib import Path

from app.browser.fleet import BrowserFleet
from app.browser.fleet_discovery import discover_browsers, BrowserInventory


async def main(submit_smoke=False, provider=None):
    root = Path(__file__).resolve().parents[1]
    inventory = discover_browsers()
    browser = next(item for item in inventory.browsers if item.name == 'Microsoft Edge')
    profile = next(item for item in inventory.profiles if item.browser_id == browser.id)
    fleet = BrowserFleet(root, inventory=BrowserInventory([browser], [profile], []), leader=False, timeout_seconds=45)
    try:
        clients = await fleet.start()
        for client in clients:
            if provider and client.provider_name != provider:
                continue
            client.use_conversation_session('input-diagnostic-' + uuid.uuid4().hex[:8])
            health = await client.probe()
            print(json.dumps({'provider': client.provider_name, 'health': health}))
            if not health.get('ready'):
                continue
            def inspect():
                transport = fleet.transport
                transport._focus(client.hwnd, client.tab_index)
                state = transport._native_snapshot(client.hwnd, client.provider_name)
                control = state.get('composer')
                if not control:
                    return {'error': state.get('error', 'missing composer')}
                rect = control['rect']
                x, y = int(rect[0]+rect[2]/2), int(rect[1]+rect[3]/2)
                return {'name': control['name'], 'rect': rect, 'runtime_id': control['runtime_id'],
                        'in_window': transport.backend.point_in_window(client.hwnd, x, y),
                        'hit': transport.backend._accessibility(client.hwnd, 'point', x, y)}
            print(json.dumps(await fleet.transport._serialized(inspect)))
            def focus():
                transport = fleet.transport
                transport._focus(client.hwnd, client.tab_index)
                control = transport._native_snapshot(client.hwnd, client.provider_name).get('composer')
                if not control:
                    return {'focused': False}
                acted = transport.backend.focus_composer(client.hwnd, control['runtime_id'])
                return {'acted': acted, 'focused': transport.backend.focused_control(client.hwnd, control['runtime_id'])}
            print(json.dumps(await fleet.transport._serialized(focus)))
            if submit_smoke:
                nonce = 'team-check-' + uuid.uuid4().hex[:12]
                try:
                    answer = await client.ask('Reply with exactly this text and nothing else: ' + nonce)
                    print(json.dumps({'provider': client.provider_name, 'reply_matches': answer.strip() == nonce,
                                      'response': answer[:1500] if answer.strip() != nonce else None}))
                except Exception as error:
                    print(json.dumps({'provider': client.provider_name, 'error': str(error)}))
                    def evidence():
                        transport = fleet.transport
                        transport._focus(client.hwnd, client.tab_index)
                        snapshot = transport.backend.accessibility_snapshot(client.hwnd)
                        binding = transport._native_bindings.get((client.hwnd, client.tab_index), {})
                        nodes = {node['id']: node for node in snapshot.get('nodes', [])}
                        related = {node['id'] for node in nodes.values() if
                                   any(word in str(node.get('name','')).lower() for word in ('said', 'response', nonce))}
                        for _ in range(4):
                            related.update(nodes[ident]['parent'] for ident in list(related) if ident in nodes)
                        return {'observed_url': snapshot.get('url'), 'bound_url': binding.get('url'),
                                'submitted': binding.get('submitted'),
                                'response_nodes': [{key: node.get(key) for key in ('id','parent','name','type','offscreen')}
                                    for node in snapshot.get('nodes', []) if node['id'] in related]}
                    print(json.dumps(await fleet.transport._serialized(evidence)))
    finally:
        await fleet.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submit-smoke', action='store_true', help='Send one nonce prompt per ready provider')
    parser.add_argument('--provider', choices=('chatgpt', 'gemini'), help='Inspect just one provider')
    options = parser.parse_args()
    asyncio.run(main(options.submit_smoke, options.provider))
