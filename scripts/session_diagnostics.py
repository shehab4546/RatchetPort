# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded hardware reports and optional Firebase delivery after a session."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import threading
import urllib.request
import urllib.parse
import uuid

MAX_REPORT = 220_000
MAX_LOG = 32_768
LOCK = threading.Lock()
PREFIXES = ('Hardware:', 'GPU ', 'GPU:', 'Audio stats ', 'ResolutionDiag ', 'Frame ',
            'Frame timing:', 'Internal resolution', 'Graphics effects:', 'Patches:',
            'Button icons:', 'Swapchain:', 'VideoOut:', 'DIAG03 ', 'Runtime: CPU time',
            'Runtime: direct memory', 'Runtime: pad reads', 'Runtime: audio ',
            'Runtime: input mapping', 'Runtime: trigger', 'The game exited')


def hardware():
    info = {'os': platform.system(), 'os_release': platform.release(),
            'architecture': platform.machine(), 'logical_cpus': os.cpu_count(),
            'cpu': platform.processor() or 'Unknown'}
    try:
        if os.name == 'nt':
            command = ("$c=Get-CimInstance Win32_Processor | Select-Object -First 1;"
                       "$m=Get-CimInstance Win32_ComputerSystem;"
                       "$g=@(Get-CimInstance Win32_VideoController | ForEach-Object {"
                       "@{name=$_.Name;driver=$_.DriverVersion}});"
                       "@{cpu=$c.Name;ram_bytes=$m.TotalPhysicalMemory;gpus=$g}|ConvertTo-Json -Compress")
            result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                capture_output=True, text=True, timeout=8,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for name in ('cpu', 'ram_bytes', 'gpus'):
                    if name in data:
                        info[name] = data[name]
        else:
            info['ram_bytes'] = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            match = re.search(r'^model name\s*:\s*(.+)$', Path('/proc/cpuinfo').read_text(), re.M)
            if match:
                info['cpu'] = match[1]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return info


def header(version):
    return 'Hardware: ' + json.dumps({'port_version': version, **hardware()}, ensure_ascii=True) + '\n'


def scrub(line):
    line = re.sub(r'https?://\S+', '[url]', line, flags=re.I)
    line = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email]', line)
    line = re.sub(r'(?i)(?:[a-z]:[\\/]|/(?:home|Users|mnt|media)/)[^\r\n]*', '[path]', line)
    line = re.sub(r'(?i)(token|password|secret|authorization|api[_-]?key)\s*[:=]\s*\S+', r'\1=[redacted]', line)
    return line[:2000]


def report(log_path, exit_code, version):
    with Path(log_path).open('rb') as stream:
        head = stream.read(128_000)
        size = stream.seek(0, 2)
        tail = b''
        if size > len(head):
            stream.seek(max(len(head), size-1_000_000))
            tail = stream.read(1_000_000)
    selected, last = [], None
    for line in (head+b'\n'+tail).decode('utf-8', 'replace').splitlines():
        if line.startswith(PREFIXES):
            clean = scrub(line)
            if clean != last:
                selected.append(clean)
                last = clean
    encoded = '\n'.join(selected).encode('utf-8')
    if len(encoded) > MAX_LOG:
        encoded = encoded[:4000] + b'\n[diagnostics truncated]\n' + encoded[-28000:]
    payload = {'schema': 1, 'id': str(uuid.uuid4()), 'version': version,
               'created_utc': datetime.now(timezone.utc).isoformat(), 'exit_code': int(exit_code),
               'log': encoded.decode('utf-8', 'ignore')}
    while len(json.dumps(payload).encode()) > MAX_REPORT:
        payload['log'] = payload['log'][:32000] + '\n[truncated]\n' + payload['log'][48000:]
    return payload


def configuration(port):
    try:
        path = Path(port)/'diagnostics.json'
        if not path.exists():
            path = Path(port)/'diagnostics.public.json'
        data = json.loads(path.read_text())
        project, key = (data[n] for n in ('project_id', 'api_key'))
        if (not isinstance(project, str) or not isinstance(key, str)
                or not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', project)
                or not re.fullmatch(r'[A-Za-z0-9_-]{20,100}', key)
                or 'endpoint' in data):
            return None
        return {'project_id': project, 'api_key': key}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def valid_report(data):
    return (isinstance(data, dict)
            and set(data) == {'schema', 'id', 'version', 'created_utc', 'exit_code', 'log'}
            and type(data['schema']) is int and data['schema'] == 1
            and isinstance(data['id'], str)
            and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', data['id']) is not None
            and isinstance(data['log'], str) and len(data['log'].encode()) <= MAX_LOG
            and isinstance(data['version'], str) and len(data['version']) <= 32
            and re.fullmatch(r'\d+(?:\.\d+){1,3}', data['version']) is not None
            and type(data['exit_code']) is int and -(2**63) <= data['exit_code'] < 2**63
            and isinstance(data['created_utc'], str) and len(data['created_utc']) <= 40)


def request_json(url, payload, token=None, *, form=False):
    headers = {'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json',
               'User-Agent': 'RatchetPort-diagnostics'}
    if token:
        headers['Authorization'] = 'Bearer '+token
    body = urllib.parse.urlencode(payload) if form else json.dumps(payload)
    request = urllib.request.Request(url, data=body.encode(), headers=headers, method='POST')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with urllib.request.build_opener(NoRedirect).open(request, timeout=12) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('Unexpected diagnostic response')
    return json.loads(raw)


def sign_in(folder, config):
    # Reuse one anonymous identity; never ship credentials in the distribution.
    path = folder.parent/'diagnostics-auth.json'
    cached = None
    try:
        cached = json.loads(path.read_text())
    except (OSError, ValueError):
        pass
    if isinstance(cached, dict) and cached.get('project_id') == config['project_id'] and cached.get('refresh_token'):
        reply = request_json('https://securetoken.googleapis.com/v1/token?key='+config['api_key'],
                             {'grant_type': 'refresh_token', 'refresh_token': cached['refresh_token']}, form=True)
        token, uid, refresh = (reply[n] for n in ('id_token', 'user_id', 'refresh_token'))
    else:
        reply = request_json('https://identitytoolkit.googleapis.com/v1/accounts:signUp?key='+config['api_key'],
                             {'returnSecureToken': True})
        token, uid, refresh = (reply[n] for n in ('idToken', 'localId', 'refreshToken'))
    if not isinstance(uid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', uid):
        raise ValueError('Invalid anonymous identity')
    atomic_json(path, {'project_id': config['project_id'], 'refresh_token': refresh})
    return token, uid


def firestore_write(payload, config, uid):
    # Immutable document and server timestamp; no Cloud Functions or Storage.
    fields = {key: ({'integerValue': str(value)} if type(value) is int else {'stringValue': value})
              for key, value in payload.items()}
    fields['uid'] = {'stringValue': uid}
    name = ('projects/'+config['project_id']+'/databases/(default)/documents/diagnostics/'
            +uid+'_'+payload['id'])
    return {'writes': [{'update': {'name': name, 'fields': fields},
                        'currentDocument': {'exists': False},
                        'updateTransforms': [{'fieldPath': 'received_at', 'setToServerValue': 'REQUEST_TIME'}]}]}


def atomic_json(path, value):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        os.chmod(tmp, 0o600)
        json.dump(value, stream, ensure_ascii=True)
    tmp.replace(path)


def send_pending(folder, config):
    # At most two accepted reports per UTC day from this installation.
    state_path = folder.parent/'diagnostics-delivery.json'
    today = datetime.now(timezone.utc).date().isoformat()
    state = {}
    try:
        state = json.loads(state_path.read_text())
    except (OSError, ValueError):
        pass
    count = state.get('count', 0) if isinstance(state, dict) and state.get('day') == today else 0
    if type(count) is not int or count < 0:
        count = 0
    files = sorted(folder.glob('*.json'), key=lambda p: p.stat().st_mtime)[:max(0, 2-count)]
    if not files:
        return
    token, uid = sign_in(folder, config)
    url = 'https://firestore.googleapis.com/v1/projects/'+config['project_id']+'/databases/(default)/documents:commit'
    for path in files:
        if path.stat().st_size > MAX_REPORT:
            continue
        payload = json.loads(path.read_text())
        if not valid_report(payload):
            continue
        reply = request_json(url, firestore_write(payload, config, uid), token)
        results = reply.get('writeResults', [])
        if len(results) != 1 or not results[0].get('updateTime') or not reply.get('commitTime'):
            raise ValueError('Diagnostic receipt mismatch')
        count += 1
        atomic_json(state_path, {'day': today, 'count': count})
        path.unlink()


def finish(settings, port, log_path, exit_code, version):
    if not settings.get('diagnostics_upload', False):
        return
    config = configuration(port)
    if not config or not LOCK.acquire(blocking=False):
        return
    folder = Path(log_path).parent/'diagnostics-pending'
    try:
        folder.mkdir(parents=True, exist_ok=True)
        payload = report(log_path, exit_code, version)
        atomic_json(folder/(payload['id']+'.json'), payload)
        files = sorted(folder.glob('*.json'), key=lambda p: p.stat().st_mtime)
        for stale in files[:-10]:
            stale.unlink()
    except (OSError, ValueError, TypeError):
        LOCK.release()
        return
    def work():
        try:
            send_pending(folder, config)
        except (OSError, ValueError, KeyError, TypeError):
            pass
        finally:
            LOCK.release()
    threading.Thread(target=work, daemon=False).start()
