"""Single-owner persistent caps for finite codec observation campaigns."""
import json
from pathlib import Path
import time


def size(path):
    path=Path(path)
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.exists() else 0


POLICIES = {
    "mq-d2-incremental-confirmation/v1": (800, 7200, 2*1024**3, 20*1024**3),
    "classic-encode-front-end/v1": (1600, 14400, 4*1024**3, 30*1024**3),
}


class Budget:
    def __init__(self, path, expected_policy=None):
        self.path=Path(path)
        self.config=json.loads(self.path.read_text())
        policy = self.config.get('policy')
        if policy not in POLICIES or (expected_policy is not None and policy != expected_policy):
            raise ValueError('budget policy differs')
        self.calls, self.seconds, self.protected_bytes, self.scratch_bytes = POLICIES[policy]
        self.state_path=self.path.with_name(self.path.stem+'-state.json')

    def before_call(self):
        # Exactly one operational owner may advance this ledger. Failed launches
        # consume their slot; no replacement or restart resets the clock.
        state=json.loads(self.state_path.read_text()) if self.state_path.exists() else dict(started_unix=time.time(),started_calls=0)
        if state['started_calls']>=self.calls or time.time()-state['started_unix']+120>self.seconds:
            raise ValueError('finite observation call/wall budget exhausted; incomplete evidence')
        if sum(size(p) for p in self.config['protected_output_roots'])>=self.protected_bytes:
            raise ValueError('protected output storage cap reached; incomplete evidence')
        if size(self.config['scratch_root'])>=self.scratch_bytes:
            raise ValueError('registered build scratch cap reached; incomplete evidence')
        state['started_calls']+=1
        self.state_path.write_text(json.dumps(state,indent=2)+'\n')
