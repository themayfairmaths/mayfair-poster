"""Mayfair Math auto-poster: posts the next unfinished block from blocks.csv to Instagram via the official API.
Runs on GitHub Actions. Secrets: IG_TOKEN (system-user token), IG_USER_ID (Instagram account ID).
Usage: python post.py check   -> verify token, account and publishing limit (posts nothing)
       python post.py post    -> post the next block (all its parts, last part first)
       python post.py test FILE.mp4 -> post one specific queue file (for a first test)"""
import csv, os, sys, time, json, datetime, urllib.request, urllib.parse, urllib.error

VER = os.environ.get('GRAPH_VERSION', 'v25.0'); G = f'https://graph.facebook.com/{VER}'
TOKEN = os.environ.get('IG_TOKEN', '').strip(); IGID = os.environ.get('IG_USER_ID', '').strip()
COVER_BASE = os.environ.get('COVER_BASE_URL', '').strip()      # e.g. https://raw.githubusercontent.com/<you>/<repo>/main/covers/  (public repo only)
LOG = 'posted.csv'; PERTH = datetime.timezone(datetime.timedelta(hours=8))

def req(method, url, params=None, data=None, headers=None):
    params = dict(params or {}); headers = dict(headers or {})
    if 'Authorization' not in headers: params['access_token'] = TOKEN
    if method == 'GET': url += '?' + urllib.parse.urlencode(params); body = None
    elif data is None: body = urllib.parse.urlencode(params).encode()
    else: url += '?' + urllib.parse.urlencode(params) if params else ''; body = data
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=300) as f: return json.loads(f.read() or b'{}')
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors='replace'); raise RuntimeError(f'{method} {url.split("?")[0]} -> {e.code}: {msg}')

def check():
    assert TOKEN, 'IG_TOKEN secret is missing'
    me = req('GET', f'{G}/me', {'fields': 'id,name'}); print('Token OK, belongs to:', me)
    assert IGID, 'IG_USER_ID secret is missing (see README)'
    acc = req('GET', f'{G}/{IGID}', {'fields': 'id,username,media_count'}); print('Instagram account:', acc)
    lim = req('GET', f'{G}/{IGID}/content_publishing_limit', {'fields': 'quota_usage,config'}); print('Publishing limit:', lim)
    print('All good - ready to post.')

def caption_for(mp4):
    t = os.path.join('queue', mp4[:-4] + '.txt'); return open(t, encoding='utf-8').read().strip() if os.path.exists(t) else ''

def post_one(mp4):
    path = os.path.join('queue', mp4); size = os.path.getsize(path)
    p = {'media_type': 'REELS', 'upload_type': 'resumable', 'caption': caption_for(mp4), 'share_to_feed': 'true'}
    cover = mp4[:-4] + ' cover.png'
    if COVER_BASE and os.path.exists(os.path.join('covers', cover)): p['cover_url'] = COVER_BASE + urllib.parse.quote(cover)
    c = req('POST', f'{G}/{IGID}/media', p); cid = c['id']; uri = c.get('uri') or f'https://rupload.facebook.com/ig-api-upload/{VER}/{cid}'
    with open(path, 'rb') as f:
        req('POST', uri, data=f.read(), headers={'Authorization': f'OAuth {TOKEN}', 'offset': '0', 'file_size': str(size), 'Content-Type': 'application/octet-stream'})
    for _ in range(60):                                             # wait up to ~10 min for processing
        st = req('GET', f'{G}/{cid}', {'fields': 'status_code,status'})
        if st.get('status_code') == 'FINISHED': break
        if st.get('status_code') in ('ERROR', 'EXPIRED'): raise RuntimeError(f'Processing failed for {mp4}: {st}')
        time.sleep(10)
    else: raise RuntimeError(f'Timed out waiting for {mp4}')
    pub = req('POST', f'{G}/{IGID}/media_publish', {'creation_id': cid}); mid = pub['id']
    link = req('GET', f'{G}/{mid}', {'fields': 'permalink'}).get('permalink', '')
    with open(LOG, 'a', newline='') as fh: csv.writer(fh).writerow([datetime.datetime.now(PERTH).strftime('%Y-%m-%d %H:%M'), mp4, link, 'posted'])
    print('Posted', mp4, link); return link

def posted():
    if not os.path.exists(LOG): return set()
    return {r[1] for r in csv.reader(open(LOG)) if len(r) > 3 and r[3] == 'posted'}

def post_next_block():
    rows = list(csv.DictReader(open('blocks.csv'))); done = posted()
    blocks = {}
    for r in rows: blocks.setdefault(int(r['block']), []).append(r)
    for b in sorted(blocks):
        todo = [r for r in sorted(blocks[b], key=lambda r: int(r['post_order'])) if r['queue_file'] not in done]
        if not todo: continue
        print(f"Block {b}: {todo[0]['block_name']} ({len(todo)} to post)")
        missing = [r['queue_file'] for r in todo if not os.path.exists(os.path.join('queue', r['queue_file']))]
        if missing: raise RuntimeError(f'Missing from queue/: {missing}')
        for r in todo: post_one(r['queue_file']); time.sleep(20)
        return
    print('Nothing left to post. Add more blocks!')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if mode == 'check': check()
    elif mode == 'post': check(); post_next_block()
    elif mode == 'test': check(); post_one(sys.argv[2])
