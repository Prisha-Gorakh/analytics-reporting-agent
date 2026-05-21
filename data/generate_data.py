import random
import time
from datetime import datetime, timedelta, timezone
from faker import Faker
import clickhouse_connect

fake = Faker()
import os
client = clickhouse_connect.get_client(host=os.getenv('CLICKHOUSE_HOST', 'localhost'), port=8123, username=os.getenv('CLICKHOUSE_USER', 'default'), password=os.getenv('CLICKHOUSE_PASSWORD'), database='analytics')

DEVICES = ['desktop', 'mobile', 'tablet']
COUNTRIES = ['US', 'IN', 'GB', 'DE', 'CA', 'AU', 'FR']
UTM_SOURCES = ['google', 'facebook', 'direct', 'email', 'twitter']
FUNNEL = ['homepage', 'product_page', 'cart', 'checkout', 'purchase']

DROP_RATES = {
    'mobile': {'cart': 0.45, 'checkout': 0.60},
    'desktop': {'cart': 0.30, 'checkout': 0.40},
    'tablet':  {'cart': 0.35, 'checkout': 0.50},
}

def simulate_session(user_id):
    session_id = fake.uuid4()
    device = random.choice(DEVICES)
    country = random.choice(COUNTRIES)
    utm = random.choice(UTM_SOURCES)
    session_start = datetime.now(timezone.utc).replace(tzinfo=None)
    events = []
    t = session_start

    for step in FUNNEL:
        drop = DROP_RATES.get(device, {}).get(step, 0.25)
        if step != 'homepage' and random.random() < drop:
            break

        t += timedelta(seconds=random.randint(5, 120))
        events.append({
            'user_id': user_id,
            'session_id': session_id,
            'event_name': f'view_{step}',
            'timestamp': t,
            'page_url': f'https://example.com/{step}',
            'device': device,
            'country': country,
            'utm_source': utm
        })

        for _ in range(random.randint(1, 4)):
            t += timedelta(seconds=random.randint(1, 15))
            replay_event = random.choices(
                ['click', 'rage_click', 'form_error', 'scroll'],
                weights=[60, 10, 10, 20]
            )[0]
            events.append({
                'user_id': user_id,
                'session_id': session_id,
                'event_name': replay_event,
                'timestamp': t,
                'page_url': f'https://example.com/{step}',
                'device': device,
                'country': country,
                'utm_source': utm
            })

    session_end = t
    return events, {
        'session_id': session_id,
        'user_id': user_id,
        'session_start': session_start,
        'session_end': session_end,
        'event_count': len(events),
        'entry_page': 'homepage',
        'exit_page': events[-1]['page_url'] if events else 'homepage',
        'device': device,
        'country': country,
        'utm_source': utm,
    }

def insert_session(user_id):
    evts, sess = simulate_session(user_id)

    client.insert('events', [
        [e['user_id'], e['session_id'], e['event_name'], e['timestamp'],
         e['page_url'], e['device'], e['country'], e['utm_source']]
        for e in evts
    ], column_names=['user_id','session_id','event_name','timestamp','page_url','device','country','utm_source'])

    client.insert('sessions', [
        [sess['session_id'], sess['user_id'], sess['session_start'], sess['session_end'],
         sess['event_count'], sess['entry_page'], sess['exit_page'], sess['device'],
         sess['country'], sess['utm_source']]
    ], column_names=['session_id','user_id','session_start','session_end','event_count','entry_page','exit_page','device','country','utm_source'])

    return len(evts)

DURATION_SECONDS = 90  # how long to run
SLEEP_BETWEEN = 7      # seconds between each new session

print(f"Live stream starting — will run for {DURATION_SECONDS}s, one session every {SLEEP_BETWEEN}s\n")

start_time = time.time()
total_events_inserted = 0
total_sessions_inserted = 0

while time.time() - start_time < DURATION_SECONDS:
    user_id = fake.uuid4()
    events_count = insert_session(user_id)

    total_events_inserted += events_count
    total_sessions_inserted += 1

    db_events = client.query("SELECT count() FROM analytics.events").result_rows[0][0]
    db_sessions = client.query("SELECT count() FROM analytics.sessions").result_rows[0][0]

    elapsed = int(time.time() - start_time)
    remaining = DURATION_SECONDS - elapsed

    print(f"[{elapsed:>3}s elapsed | {remaining:>3}s left] "
          f"This run: +{events_count} events, +1 session | "
          f"DB total: {db_events:,} events, {db_sessions:,} sessions")

    time.sleep(SLEEP_BETWEEN)

print(f"\nDone! Inserted {total_events_inserted} events and {total_sessions_inserted} sessions in {DURATION_SECONDS}s")