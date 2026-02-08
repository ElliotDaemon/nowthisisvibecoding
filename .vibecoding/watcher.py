#!/usr/bin/env python3
"""Background watcher that polls for new user messages from the web UI.
Writes new messages to .vibecoding/.pending for Claude to pick up.
"""
import json, subprocess, sys, os, time

REPO = '/home/user/nowthisisvibecoding'
INPUT_FILE = os.path.join(REPO, '.vibecoding/input.json')
PENDING_FILE = os.path.join(REPO, '.vibecoding/.pending')
PROCESSED_FILE = os.path.join(REPO, '.vibecoding/.last_processed_ts')
BRANCH = 'claude/interactive-web-interface-rB0iQ'
POLL_INTERVAL = 5  # seconds


def git(*args):
    r = subprocess.run(
        ['git'] + list(args),
        capture_output=True, text=True, cwd=REPO,
        timeout=15
    )
    return r


def get_last_processed():
    try:
        with open(PROCESSED_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def set_last_processed(ts):
    with open(PROCESSED_FILE, 'w') as f:
        f.write(str(ts))


def check_for_messages():
    """Pull latest and check for new messages. Returns list of new messages."""
    try:
        git('fetch', 'origin', BRANCH)
        git('merge', 'origin/' + BRANCH, '--ff-only')
    except Exception:
        pass

    try:
        with open(INPUT_FILE) as f:
            data = json.load(f)
    except Exception:
        return []

    last_ts = get_last_processed()
    new_msgs = []
    new_responses = []

    for msg in data.get('messages', []):
        if msg.get('ts', 0) > last_ts:
            new_msgs.append(msg)

    for resp in data.get('responses', []):
        if resp.get('ts', 0) > last_ts:
            new_responses.append(resp)

    brief_action = data.get('briefAction')
    if brief_action and brief_action.get('ts', 0) > last_ts:
        new_responses.append({'type': 'briefAction', **brief_action})

    return new_msgs, new_responses


def write_pending(messages):
    """Write pending messages for Claude to pick up."""
    with open(PENDING_FILE, 'w') as f:
        json.dump(messages, f, indent=2)


def main():
    print(f"[watcher] Starting message watcher (polling every {POLL_INTERVAL}s)")
    print(f"[watcher] Watching: {INPUT_FILE}")
    print(f"[watcher] Pending file: {PENDING_FILE}")
    sys.stdout.flush()

    # Initialize last processed to current latest message
    try:
        with open(INPUT_FILE) as f:
            data = json.load(f)
        msgs = data.get('messages', [])
        if msgs:
            latest_ts = max(m.get('ts', 0) for m in msgs)
            current = get_last_processed()
            if current < latest_ts:
                # Don't re-process old messages on startup
                set_last_processed(latest_ts)
                print(f"[watcher] Initialized last_processed to {latest_ts}")
    except Exception:
        pass

    sys.stdout.flush()

    while True:
        try:
            new_msgs, new_responses = check_for_messages()
            all_items = []
            if new_msgs:
                for m in new_msgs:
                    content = m.get('content', '')
                    print(f"\n[NEW MESSAGE] {content}")
                    sys.stdout.flush()
                all_items.extend(new_msgs)

            if new_responses:
                for r in new_responses:
                    if r.get('type') == 'briefAction':
                        print(f"\n[BRIEF ACTION] {r.get('action', '')}")
                    else:
                        print(f"\n[RESPONSE] {r.get('questionId', '')}: {r.get('value', [])}")
                    sys.stdout.flush()
                all_items.extend(new_responses)

            if all_items:
                write_pending(all_items)
                latest = max(item.get('ts', 0) for item in all_items)
                set_last_processed(latest)

        except Exception as e:
            print(f"[watcher] Error: {e}", file=sys.stderr)
            sys.stderr.flush()

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
