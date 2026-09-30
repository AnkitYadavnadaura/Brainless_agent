"""One visible Blender process receiving trusted compiler jobs via a local queue."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid


class LiveBlenderSession:
    def __init__(self, blender, workspace):
        self.blender=blender
        self.root=Path(workspace).resolve()/'.live-blender'
        self.root.mkdir(parents=True,exist_ok=True)
        self.process=None
        self.lock=asyncio.Lock()

    async def ensure_started(self):
        heartbeat=self.root/'heartbeat.json'
        if self.process is not None and self.process.poll() is None:
            return
        # A stale heartbeat from another CLI must not create a second Blender
        # while its main thread is busy rendering.
        if heartbeat.exists():
            import psutil
            try:
                state=json.loads(heartbeat.read_text(encoding='utf-8'))
                process=psutil.Process(state['pid'])
                if process.is_running() and 'blender' in process.name().lower():
                    if time.time()-state['time']<5:
                        return
                    raise RuntimeError('Existing Blender is busy or unresponsive; keep this checkpoint and retry when it responds.')
            except (psutil.NoSuchProcess,OSError,ValueError,KeyError):
                pass
        heartbeat.unlink(missing_ok=True)
        (self.root/'command.json').unlink(missing_ok=True)
        runtime=Path(__file__).with_name('live_blender_runtime.py')
        with (self.root/'worker.log').open('ab') as log:
            self.process=subprocess.Popen([self.blender,'--python',str(runtime),'--',str(self.root)],
                stdout=log,stderr=log,cwd=str(self.root))
        deadline=time.monotonic()+90
        while not heartbeat.exists():
            if self.process.poll() is not None:
                raise RuntimeError('Visible Blender failed to start; see .live-blender/worker.log')
            if time.monotonic()>deadline:
                self.process.terminate()
                raise RuntimeError('Visible Blender startup timed out')
            await asyncio.sleep(.2)

    async def run(self, script, source, project, *, animate=False, timeout=7200, focus_object=None, focus_view=True):
        from app.autonomy.village_projects import project_lock
        async with self.lock:
            with project_lock(self.root,'worker'):
                await self.ensure_started()
                ident=uuid.uuid4().hex
                script=Path(script).resolve()
                command=dict(id=ident,script=str(script),sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                             source=str(Path(source).resolve()) if source else None,
                             project=str(Path(project).resolve()),animate=bool(animate),
                             focus_object=focus_object,focus_view=bool(focus_view))
                target=self.root/'command.json'
                temporary=target.with_suffix('.tmp')
                temporary.write_text(json.dumps(command),encoding='utf-8')
                temporary.replace(target)
                result=self.root/f'{ident}.json'
                deadline=time.monotonic()+timeout
                try:
                    while not result.exists():
                        if self.process is not None and self.process.poll() is not None:
                            raise RuntimeError('Visible Blender closed during a step; retrying can restore the checkpoint')
                        if time.monotonic()>deadline:
                            if self.process is not None:
                                self.process.terminate()
                            raise RuntimeError('Visible Blender step timed out')
                        await asyncio.sleep(.2)
                    evidence=json.loads(result.read_text(encoding='utf-8'))
                    if evidence.get('status')!='completed':
                        raise RuntimeError('Visible Blender step failed: '+str(evidence.get('error')))
                except asyncio.CancelledError:
                    if self.process is not None and self.process.poll() is None:
                        self.process.terminate()
                    raise
                finally:
                    result.unlink(missing_ok=True)
