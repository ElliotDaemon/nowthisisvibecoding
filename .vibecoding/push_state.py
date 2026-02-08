#!/usr/bin/env python3
"""Helper to push state.json updates with optional embedded preview HTML.

Usage:
  python3 .vibecoding/push_state.py --status building --build-step "Generating..." --build-percent 10
  python3 .vibecoding/push_state.py --status idle --preview-html preview/index.html -m "Done!"
  python3 .vibecoding/push_state.py --add-file preview/index.html
"""
import json, subprocess, sys, os, time, argparse

REPO = '/home/user/nowthisisvibecoding'
STATE_FILE = '.vibecoding/state.json'
BRANCH = 'claude/interactive-web-interface-rB0iQ'


def git(*args):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        print(f'git {" ".join(args)}: {r.stderr.strip()}', file=sys.stderr)
    return r


def read_state():
    path = os.path.join(REPO, STATE_FILE)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {
            "v": 2, "ts": 0, "status": "idle", "statusText": "",
            "messages": [], "files": {}, "terminal": [],
            "activeFile": None, "buildProgress": None,
            "previewHtml": None, "previewUrl": None,
            "suggestedActions": []
        }


def write_state(state, commit_msg="update state"):
    state['ts'] = int(time.time() * 1000)
    path = os.path.join(REPO, STATE_FILE)
    with open(path, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    git('add', STATE_FILE)
    git('commit', '-m', commit_msg)
    return push()


def push():
    for i in range(4):
        r = git('push', '-u', 'origin', BRANCH)
        if r.returncode == 0:
            print('Pushed successfully.')
            return True
        wait = 2 ** (i + 1)
        print(f'Push failed, retrying in {wait}s...', file=sys.stderr)
        time.sleep(wait)
    print('Push failed after 4 retries.', file=sys.stderr)
    return False


def main():
    p = argparse.ArgumentParser(description='Push vibecoding state updates')
    p.add_argument('--status', help='Set status: idle, building, working, error')
    p.add_argument('--status-text', help='Status display text')
    p.add_argument('-m', '--message', help='Add an assistant message')
    p.add_argument('--preview-html', help='Path to HTML file to embed as srcdoc preview')
    p.add_argument('--preview-url', help='Relative URL for iframe preview')
    p.add_argument('--clear-preview', action='store_true', help='Clear both preview fields')
    p.add_argument('--build-step', help='Build progress step label')
    p.add_argument('--build-percent', type=int, help='Build progress percentage (0-100)')
    p.add_argument('--build-substep', help='Build progress substep text')
    p.add_argument('--clear-build', action='store_true', help='Clear build progress')
    p.add_argument('--add-file', action='append', help='Add file to files dict (reads content)')
    p.add_argument('--add-terminal', action='append', nargs=2, metavar=('TYPE', 'TEXT'),
                   help='Add terminal line: --add-terminal info "Starting build"')
    p.add_argument('--clear-terminal', action='store_true')
    p.add_argument('--actions', help='JSON array of suggested actions')
    p.add_argument('--questionnaire', help='JSON object for questionnaire (intake/checkpoint)')
    p.add_argument('--clear-questionnaire', action='store_true', help='Clear questionnaire')
    p.add_argument('--brief', help='JSON object for brief review on current questionnaire')
    p.add_argument('--commit-msg', default='update state', help='Git commit message')
    args = p.parse_args()

    state = read_state()

    if args.status:
        state['status'] = args.status
    if args.status_text:
        state['statusText'] = args.status_text

    if args.message:
        state['messages'].append({
            "id": f"claude_{int(time.time())}",
            "role": "assistant",
            "content": args.message,
            "ts": int(time.time() * 1000)
        })

    if args.preview_html:
        html_path = os.path.join(REPO, args.preview_html) if not os.path.isabs(args.preview_html) else args.preview_html
        with open(html_path) as f:
            state['previewHtml'] = f.read()
        state['previewUrl'] = None

    if args.preview_url:
        state['previewUrl'] = args.preview_url
        state['previewHtml'] = None

    if args.clear_preview:
        state['previewHtml'] = None
        state['previewUrl'] = None

    if args.build_step or args.build_percent is not None or args.build_substep:
        if not state.get('buildProgress'):
            state['buildProgress'] = {}
        if args.build_step:
            state['buildProgress']['currentStep'] = args.build_step
        if args.build_percent is not None:
            state['buildProgress']['percent'] = args.build_percent
        if args.build_substep:
            state['buildProgress']['substep'] = args.build_substep

    if args.clear_build:
        state['buildProgress'] = None

    if args.add_file:
        if not state.get('files'):
            state['files'] = {}
        for fpath in args.add_file:
            full = os.path.join(REPO, fpath) if not os.path.isabs(fpath) else fpath
            with open(full) as f:
                state['files'][fpath] = f.read()

    if args.clear_terminal:
        state['terminal'] = []

    if args.add_terminal:
        for ttype, ttext in args.add_terminal:
            state['terminal'].append({"type": ttype, "content": ttext})

    if args.actions:
        state['suggestedActions'] = json.loads(args.actions)

    if args.questionnaire:
        state['questionnaire'] = json.loads(args.questionnaire)

    if args.clear_questionnaire:
        state['questionnaire'] = None

    if args.brief:
        if state.get('questionnaire'):
            state['questionnaire']['phase'] = 'review'
            state['questionnaire']['brief'] = json.loads(args.brief)

    write_state(state, args.commit_msg)


if __name__ == '__main__':
    main()
