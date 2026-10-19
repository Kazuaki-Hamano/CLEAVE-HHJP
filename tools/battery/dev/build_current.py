import contextlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

with contextlib.redirect_stdout(io.StringIO()):
    helper = runpy.run_path('tools/battery/github_build.py')
get = helper['get']
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
runs = json.loads(get('/actions/runs?branch=battery/peripheral-fetch&per_page=20'))['workflow_runs']
matches = [r for r in runs if r['head_sha'] == sha and r['name'] == 'Build ZMK firmware']
if not matches:
    print('Waiting for build run for', sha[:8])
    raise SystemExit(0)
run = matches[0]
print(json.dumps({k: run[k] for k in ('id', 'head_sha', 'status', 'conclusion', 'html_url')}))
if run['status'] != 'completed':
    jobs = json.loads(get(f"/actions/runs/{run['id']}/jobs"))['jobs']
    print(json.dumps([{'name': j['name'], 'status': j['status'], 'conclusion': j['conclusion']} for j in jobs]))
elif run['conclusion'] != 'success':
    raise SystemExit('Build did not succeed')
elif sys.argv[-1] == 'download':
    root = Path('output/firmware') / sha[:8]
    root.mkdir(parents=True, exist_ok=True)
    artifacts = json.loads(get(f"/actions/runs/{run['id']}/artifacts"))['artifacts']
    for artifact in artifacts:
        data = get(f"/actions/artifacts/{artifact['id']}/zip")
        (root / (artifact['name'] + '.zip')).write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip():
                raise RuntimeError('Artifact ZIP integrity failed')
            archive.extractall(root)
    (root / 'build-logs.zip').write_bytes(get(f"/actions/runs/{run['id']}/logs"))
    print('Downloaded to', root)
