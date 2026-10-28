"""Free public X timeline monitor. Python standard library only."""
import argparse
import json
import os
from pathlib import Path
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

USERNAME = 'thsottiaux'
USER_ID = '1953337039510003712'


def request(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'tibo-mail-monitor/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.load(response)
    if data.get('code') != 200 or data.get('stale') is True or data.get('errors') is not None:
        raise ValueError('Source returned unsuccessful/stale data')
    return data


def fetch_posts(since=None):
    posts, cursors = {}, set()
    url = f'https://api.fxtwitter.com/2/profile/id:{USER_ID}/statuses?count=100&with_replies=1'
    for _ in range(100):
        data = request(url)
        rows, cursor = data.get('results'), data.get('cursor')
        if not isinstance(rows, list) or not isinstance(cursor, dict):
            raise ValueError('Invalid timeline structure')
        ids = []
        for row in rows:
            if row.get('type') != 'status' or not str(row.get('id', '')).isdigit() or not isinstance(row.get('author'), dict):
                raise ValueError('Invalid timeline entry')
            post_id = str(row['id'])
            ids.append(int(post_id))
            if str(row['author'].get('id')) != USER_ID or row.get('reposted_by') is not None:
                continue
            if since and int(post_id) <= int(since):
                continue
            text = (row.get('raw_text') or {}).get('text', row.get('text'))
            if not isinstance(text, str):
                raise ValueError('Missing post text')
            posts[post_id] = {'id': post_id, 'text': text, 'url': f'https://x.com/{USERNAME}/status/{post_id}'}
        next_cursor = cursor.get('bottom')
        if since is None or (ids and max(ids) <= int(since)) or not next_cursor:
            return sorted(posts.values(), key=lambda post: int(post['id']))
        if not isinstance(next_cursor, str) or next_cursor in cursors:
            raise ValueError('Invalid/repeated pagination cursor')
        cursors.add(next_cursor)
        url = f'https://api.fxtwitter.com/2/profile/id:{USER_ID}/statuses?' + urllib.parse.urlencode({'count': 100, 'with_replies': 1, 'cursor': next_cursor})
    raise ValueError('Pagination limit reached; state was not advanced')


def send_mail(posts, test=False):
    sender = os.environ['QQ_EMAIL']
    password = os.environ['QQ_AUTH_CODE'].replace(' ', '')
    recipient = os.environ.get('EMAIL_TO') or sender
    message = EmailMessage()
    message['From'], message['To'] = sender, recipient
    message['Subject'] = 'Tibo monitor test' if test else f'Tibo: {len(posts)} new X posts'
    message.set_content('Test notification: email delivery works.' if test else '\n\n'.join(post['text'] + '\n' + post['url'] for post in posts))
    with smtplib.SMTP_SSL('smtp.qq.com', 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def run(path, dry_run=False):
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'since': None, 'pending': []}
    if not dry_run and state['pending']:
        send_mail(state['pending'])
        state['pending'] = []
        save(path, state)
    posts = fetch_posts(state['since'])
    if dry_run:
        print(f'Source verified: {len(posts)} eligible posts; no mail sent or state written.')
        return
    if state['since'] is None:
        if not posts:
            raise ValueError('Cannot establish baseline from empty timeline')
        state['since'] = posts[-1]['id']
        save(path, state)
        print('Baseline saved; historical posts were not sent.')
        return
    known = {post['id'] for post in state['pending']}
    state['pending'].extend(post for post in posts if post['id'] not in known)
    if posts:
        state['since'] = posts[-1]['id']
    save(path, state)
    if state['pending']:
        send_mail(state['pending'])
        state['pending'] = []
        save(path, state)
        print('Notification sent.')
    else:
        print('No new posts.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, default=Path('runtime/state.json'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--test-email', action='store_true')
    args = parser.parse_args()
    try:
        if args.test_email:
            send_mail([], test=True)
            print('Test email sent.')
        else:
            run(args.state, args.dry_run)
    except Exception as error:
        # Do not print exception text: provider errors may include credentials.
        print(f'Monitor failed ({type(error).__name__}); check source availability and Secrets.')
        raise SystemExit(1)
