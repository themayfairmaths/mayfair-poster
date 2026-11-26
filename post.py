"""Mayfair Math auto-poster: posts the next unfinished block from blocks.csv to Instagram via the official API.
Runs on GitHub Actions. Secrets: IG_TOKEN (system-user token), IG_USER_ID (Instagram account ID).
Usage: python post.py check   -> verify token, account and publishing limit (posts nothing)
       python post.py post    -> post ONE reel: the next part of today's block (hourly 08:00-15:00 Perth, one block per day)
       python post.py test FILE.mp4 -> post one specific queue file (for a first test)
       python post.py carousel [FOLDER] -> post the next carousel that is due (or one named folder)
Carousels: carousels.csv (after_block,folder,carousel_name[,post_date YYYY-MM-DD]) + carousels/<folder>/slide01.jpg ... slide10.jpg + caption.txt.
A carousel with a post_date is due from midday on that date. Otherwise it is due once every reel in its after_block was posted on an EARLIER day (Perth time), so it goes out at
midday the day after its reels. One carousel per run. Needs a public repo (Instagram fetches the JPEGs by URL)."""
import csv, os, sys, time, json, datetime, urllib.request, urllib.parse, urllib.error

VER = os.environ.get('GRAPH_VERSION', 'v25.0'); G = f'https://graph.facebook.com/{VER}'
TOKEN = os.environ.get('IG_TOKEN', '').strip(); IGID = os.environ.get('IG_USER_ID', '').strip()
COVER_BASE = os.environ.get('COVER_BASE_URL', '').strip()      # e.g. https://raw.githubusercontent.com/<you>/<repo>/main/covers/  (public repo only)
CAR_BASE = os.environ.get('CAROUSEL_BASE_URL', '').strip() or COVER_BASE.replace('/covers/', '/carousels/')
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

BUSINESS_ID = os.environ.get('BUSINESS_ID', '2181762142082848')   # Meta business portfolio "Adam Lichtman" (not a secret)

def discover():
    """Print every Instagram account this token can see, with its ID (for the IG_USER_ID secret). Never fails."""
    found = {}
    tries = [('Instagram accounts assigned to this system user', f'{G}/me/assigned_instagram_accounts', {'fields': 'id,username'}),
             ('Pages this token can manage', f'{G}/me/accounts', {'fields': 'name,instagram_business_account{id,username}'}),
             ('Business portfolio: Instagram business accounts', f'{G}/{BUSINESS_ID}/instagram_business_accounts', {'fields': 'id,username'}),
             ('Business portfolio: owned Instagram accounts', f'{G}/{BUSINESS_ID}/owned_instagram_accounts', {'fields': 'id,username'}),
             ('Business portfolio: owned Pages', f'{G}/{BUSINESS_ID}/owned_pages', {'fields': 'name,instagram_business_account{id,username}'})]
    for label, url, p in tries:
        try:
            data = req('GET', url, p).get('data', [])
            print(f'- {label}: {len(data)} found')
            for d in data:
                ig = d.get('instagram_business_account') or (d if 'username' in d else None)
                if ig: found[ig['id']] = ig.get('username', '?'); print(f"    @{ig.get('username', '?')}  ID = {ig['id']}" + (f"  (via Page '{d['name']}')" if 'name' in d else ''))
                elif 'name' in d: print(f"    Page '{d['name']}' has no Instagram account linked")
        except Exception as e:
            print(f'- {label}: not available ({str(e)[:160]})')
    if found:
        print('\n>>> Copy the ID next to @themayfairmaths into a new repository secret called IG_USER_ID, then run check again.')
    else:
        print('\n>>> No Instagram account visible to this token. Send Claude this log (it contains no secrets).')

def check():
    assert TOKEN, 'IG_TOKEN secret is missing'
    me = req('GET', f'{G}/me', {'fields': 'id,name'}); print('Token OK, belongs to:', me)
    if not IGID:
        print('IG_USER_ID secret is missing - looking for your Instagram account ID instead:'); discover(); sys.exit(1)
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

def posted(with_dates=False):
    if not os.path.exists(LOG): return {} if with_dates else set()
    rows = [r for r in csv.reader(open(LOG)) if len(r) > 3 and r[3] == 'posted']
    return {r[1]: r[0][:10] for r in rows} if with_dates else {r[1] for r in rows}

def wait_ready(cid, what):
    for _ in range(60):
        st = req('GET', f'{G}/{cid}', {'fields': 'status_code,status'})
        if st.get('status_code') in ('FINISHED', None): return
        if st.get('status_code') in ('ERROR', 'EXPIRED'): raise RuntimeError(f'Processing failed for {what}: {st}')
        time.sleep(5)
    raise RuntimeError(f'Timed out waiting for {what}')

def post_carousel(folder):
    """Instagram carousel from carousels/<folder>/slide*.jpg (JPEG only, 2-10 slides) + caption.txt."""
    assert CAR_BASE, 'Set COVER_BASE_URL (or CAROUSEL_BASE_URL) - Instagram fetches carousel images by public URL'
    d = os.path.join('carousels', folder)
    slides = sorted(f for f in os.listdir(d) if f.lower().startswith('slide') and f.lower().endswith(('.jpg', '.jpeg')))
    if not 2 <= len(slides) <= 10: raise RuntimeError(f'{folder}: need 2-10 JPEG slides, found {len(slides)}')
    cap = os.path.join(d, 'caption.txt'); caption = open(cap, encoding='utf-8').read().strip() if os.path.exists(cap) else ''
    kids = []
    for f in slides:
        url = CAR_BASE + urllib.parse.quote(folder) + '/' + urllib.parse.quote(f)
        c = req('POST', f'{G}/{IGID}/media', {'image_url': url, 'is_carousel_item': 'true'}); wait_ready(c['id'], f); kids.append(c['id'])
    c = req('POST', f'{G}/{IGID}/media', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'caption': caption}); wait_ready(c['id'], folder)
    mid = req('POST', f'{G}/{IGID}/media_publish', {'creation_id': c['id']})['id']
    link = req('GET', f'{G}/{mid}', {'fields': 'permalink'}).get('permalink', '')
    with open(LOG, 'a', newline='') as fh: csv.writer(fh).writerow([datetime.datetime.now(PERTH).strftime('%Y-%m-%d %H:%M'), 'carousel:' + folder, link, 'posted'])
    print('Posted carousel', folder, link); return link

def post_next_carousel():
    if not os.path.exists('carousels.csv'): print('No carousels.csv - nothing to do.'); return
    done = posted(with_dates=True); today = datetime.datetime.now(PERTH).strftime('%Y-%m-%d')
    blocks = {}
    if os.path.exists('blocks.csv'):
        for r in csv.DictReader(open('blocks.csv')): blocks.setdefault(int(r['block']), []).append(r['queue_file'])
    rows = list(csv.DictReader(open('carousels.csv')))
    for r in sorted(rows, key=lambda r: (r.get('post_date') or '9999', int(r.get('after_block') or 0))):
        if 'carousel:' + r['folder'] in done: continue
        if (r.get('post_date') or '').strip():                 # dated carousel: due from 12:00 on that Perth date
            if r['post_date'].strip() > today: print(f"Next carousel '{r['carousel_name']}' is planned for {r['post_date']}."); return
            post_carousel(r['folder']); return
        files = blocks.get(int(r['after_block']), [])
        if not files or any(f not in done for f in files): print(f"Next carousel '{r['carousel_name']}' waits for block {r['after_block']}."); return
        if max(done[f] for f in files) >= today: print(f"Block {r['after_block']} went out today - '{r['carousel_name']}' goes tomorrow at midday."); return
        post_carousel(r['folder']); return
    print('No carousels waiting.')

GAP_MIN = int(os.environ.get('MIN_GAP_MINUTES', '45'))           # never two reels closer than this

def post_next_reel():
    """Post ONE reel: the next part of the current block. Runs hourly 08:00-15:00 Perth.
    A new block only starts if no block has started today, so one block goes out per day, one reel per hour."""
    now = datetime.datetime.now(PERTH); today = now.strftime('%Y-%m-%d')
    rows = list(csv.DictReader(open('blocks.csv'))); log = {}
    if os.path.exists(LOG):
        for r in csv.reader(open(LOG)):
            if len(r) > 3 and r[3] == 'posted' and not r[1].startswith(('carousel:', '000 ')):
                log[r[1]] = datetime.datetime.strptime(r[0][:16], '%Y-%m-%d %H:%M').replace(tzinfo=PERTH)
    if log and (now - max(log.values())).total_seconds() < GAP_MIN * 60:
        print(f'Last reel went out under {GAP_MIN} min ago - waiting for the next run.'); return
    blocks = {}
    for r in rows: blocks.setdefault(int(r['block']), []).append(r)
    for b in sorted(blocks):
        parts = sorted(blocks[b], key=lambda r: int(r['post_order']))
        todo = [r for r in parts if r['queue_file'] not in log]
        if not todo: continue
        if not any(r['queue_file'] in log for r in parts):          # fresh block: only if no block started today
            for bb in sorted(blocks):
                first = [log[r['queue_file']] for r in blocks[bb] if r['queue_file'] in log]
                if first and min(first).strftime('%Y-%m-%d') == today:
                    print(f"Today's block (block {bb}) has started or finished - block {b} starts tomorrow at 08:00."); return
        r = todo[0]
        print(f"Block {b}: {r['block_name']} - posting {r['queue_file']} ({len(todo) - 1} left after this)")
        if not os.path.exists(os.path.join('queue', r['queue_file'])): raise RuntimeError(f"Missing from queue/: {r['queue_file']}")
        post_one(r['queue_file']); return
    print('Nothing left to post. Add more blocks!')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if mode == 'check': check()
    elif mode == 'post': check(); post_next_reel()
    elif mode == 'test': check(); post_one(sys.argv[2])
    elif mode == 'carousel':
        check()
        if len(sys.argv) > 2 and sys.argv[2].strip(): post_carousel(sys.argv[2].strip())
        else: post_next_carousel()
