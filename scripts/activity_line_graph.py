"""Generate an SVG from GitHub's last seven completed UTC calendar days."""
import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import urllib.request


def render(days, username):
    if len(days) != 7:
        raise ValueError('Expected seven contribution days')
    values = [int(d['contributionCount']) for d in days]
    if min(values) < 0:
        raise ValueError('Negative contribution count')
    step = max(1, math.ceil(max(values) / 4))
    ceiling = step * 4
    left, top, width, height = 85, 90, 740, 260
    x = lambda i: left + i * width / 6
    y = lambda v: top + height - v * height / ceiling
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="460" viewBox="0 0 920 460" role="img" aria-labelledby="title desc">',
             '<title id="title">GitHub contribution line graph</title>',
             '<desc id="desc">' + html.escape(', '.join(f"{d['date']}: {v} contributions" for d, v in zip(days, values))) + '</desc>',
             '<rect width="920" height="460" rx="18" fill="#cfcfcf"/>',
             '<g font-family="Arial, sans-serif" fill="#262626">',
             f'<text x="85" y="36" font-size="23" font-weight="700">{html.escape(username)} — Contributions</text>',
             '<text x="85" y="62" font-size="14">Last 7 completed UTC days · GitHub calendar counts</text>']
    for i in range(5):
        value = i * step
        parts += [f'<path d="M {left} {y(value)} H {left+width}" stroke="#8652cf" stroke-width="1"/>',
                  f'<text x="72" y="{y(value)+6}" text-anchor="end" font-size="18">{value}</text>']
    for i, day in enumerate(days):
        date = dt.date.fromisoformat(day['date'])
        parts += [f'<path d="M {x(i)} {top} V {top+height}" stroke="#8652cf" stroke-width="1"/>',
                  f'<text x="{x(i)}" y="383" text-anchor="middle" font-size="18" font-weight="700">{date:%a}</text>',
                  f'<text x="{x(i)}" y="405" text-anchor="middle" font-size="13">{date:%d %b}</text>']
    parts += ['<path d="M85 74 V350 H844" fill="none" stroke="#6d28d9" stroke-width="3"/>',
              '<path d="M85 70 L77 85 H93 Z M852 350 L837 342 V358 Z" fill="#6d28d9"/>']
    points = ' '.join(f'{x(i):.2f},{y(v):.2f}' for i, v in enumerate(values))
    parts.append(f'<polyline points="{points}" fill="none" stroke="#2783de" stroke-width="3" stroke-linejoin="round"/>')
    for i, v in enumerate(values):
        parts += [f'<circle cx="{x(i)}" cy="{y(v)}" r="6" fill="#2783de"/>',
                  f'<text x="{x(i)}" y="{y(v)-12}" text-anchor="middle" font-size="15" font-weight="700">{v}</text>']
    parts.append(f'<text x="85" y="439" font-size="13">{days[0]["date"]} to {days[-1]["date"]} · Total: {sum(values)}</text></g></svg>')
    return '\n'.join(parts)


def main():
    username = os.environ.get('GH_USERNAME', 'ankit-kr-maurya-82')
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=7)
    end = dt.datetime.combine(today, dt.time(), dt.timezone.utc) - dt.timedelta(seconds=1)
    query = '''query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) { contributionsCollection(from:$from,to:$to) {
        contributionCalendar { weeks { contributionDays { date contributionCount } } }
      } }
    }'''
    payload = {'query': query, 'variables': {'login': username,
               'from': f'{start}T00:00:00Z', 'to': end.isoformat()}}
    request = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps(payload).encode(), headers={
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
            'Content-Type': 'application/json', 'User-Agent': 'profile-line-graph'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    if data.get('errors'):
        raise RuntimeError('GitHub GraphQL error: ' + json.dumps(data['errors']))
    user = data['data']['user']
    if not user:
        raise RuntimeError('GitHub user not found')
    weeks = user['contributionsCollection']['contributionCalendar']['weeks']
    by_date = {d['date']: d for w in weeks for d in w['contributionDays']}
    expected = [(start + dt.timedelta(days=i)).isoformat() for i in range(7)]
    if any(date not in by_date for date in expected):
        raise RuntimeError('Incomplete calendar response; keeping previously published graph')
    days = [by_date[date] for date in expected]
    Path('dist').mkdir(exist_ok=True)
    Path('dist/activity-line.svg').write_text(render(days, username), encoding='utf-8')
    print('Created dist/activity-line.svg from GitHub contribution data')


if __name__ == '__main__':
    main()
