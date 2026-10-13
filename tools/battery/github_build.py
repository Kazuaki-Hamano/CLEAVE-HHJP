import json
import pathlib
import subprocess
import sys
import urllib.request
import zipfile
import io
import time

repo = 'Kazuaki-Hamano/CLEAVE-HHJP'
p = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', text=True, capture_output=True, check=True)
credential = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirect = super().redirect_request(req, fp, code, msg, headers, newurl)
        redirect.remove_header('Authorization')
        return redirect
opener = urllib.request.build_opener(SafeRedirect())
def get(path):
    path += ('&' if '?' in path else '?') + 'nocache=' + str(time.time_ns())
    request = urllib.request.Request('https://api.github.com/repos/' + repo + path,
        headers={'Authorization': 'Bearer ' + credential['password'], 'Accept': 'application/vnd.github+json'})
    return opener.open(request).read()

runs = json.loads(get('/actions/runs?branch=battery/peripheral-fetch&per_page=5'))['workflow_runs']
run = runs[0]
print(run['id'], run['status'], run['conclusion'], run['html_url'])
if run['status'] == 'completed' and sys.argv[-1] == 'download':
    root = pathlib.Path('output/firmware') / run['head_sha'][:8]
    root.mkdir(parents=True, exist_ok=True)
    artifacts = json.loads(get('/actions/runs/' + str(run['id']) + '/artifacts'))['artifacts']
    for artifact in artifacts:
        data = get('/actions/artifacts/' + str(artifact['id']) + '/zip')
        (root / (artifact['name'] + '.zip')).write_bytes(data)
        zipfile.ZipFile(io.BytesIO(data)).extractall(root)
    (root / 'build-logs.zip').write_bytes(get('/actions/runs/' + str(run['id']) + '/logs'))
    print('Downloaded to', root)
