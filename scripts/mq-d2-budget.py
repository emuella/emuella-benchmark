"""Single-owner persistent cap for all MQ D2 codec observation processes."""
import json
from pathlib import Path
import time


def size(path):
    path=Path(path)
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.exists() else 0


class Budget:
    def __init__(self, path):
        self.path=Path(path)
        self.config=json.loads(self.path.read_text())
        if self.config.get('policy')!='mq-d2-incremental-confirmation/v1':
            raise ValueError('budget policy differs')
        self.state_path=self.path.with_name(self.path.stem+'-state.json')

    def before_call(self):
        # Exactly one operational owner may advance this ledger. Failed launches
        # consume their slot; no replacement or restart resets the clock.
        state=json.loads(self.state_path.read_text()) if self.state_path.exists() else dict(started_unix=time.time(),started_calls=0)
        if state['started_calls']>=800 or time.time()-state['started_unix']+120>7200:
            raise ValueError('finite observation call/wall budget exhausted; incomplete evidence')
        if sum(size(p) for p in self.config['protected_output_roots'])>=2*1024**3:
            raise ValueError('protected output storage cap reached; incomplete evidence')
        if size(self.config['scratch_root'])>=20*1024**3:
            raise ValueError('registered build scratch cap reached; incomplete evidence')
        state['started_calls']+=1
        self.state_path.write_text(json.dumps(state,indent=2)+'\n')
