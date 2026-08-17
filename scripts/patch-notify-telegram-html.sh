#!/usr/bin/env bash
# Give /usr/local/sbin/notify-telegram HTML rendering, with a plain-text
# fallback so formatting can never cost delivery.
#
#   sudo /opt/ai-agent-platform/scripts/patch-notify-telegram-html.sh
#
# WHY. Neither Telegram sender set parse_mode, so every **bold**, ### heading
# and ``` fence our agents write arrived as literal punctuation. HTML is the
# right mode: MarkdownV2 demands escaping `_ * [ ] ( ) ~ > # + - = | { } . !`,
# all of which appear constantly in paths, diffs and ordinary prose, and one
# missed escape means HTTP 400 and a message that is never delivered.
#
# WHAT CHANGES. The send gains parse_mode=HTML. Input is HTML-escaped by
# default, which is invisible for the plain prose that backup.sh and the
# predictor pipelines send. Callers that have already produced HTML — the
# Python ones, via agents/telegram_format.py — pass --html to skip escaping.
# On any non-ok response the send is retried once with no parse_mode.
#
# The helper has no source copy in any repo; it exists only at /usr/local/sbin
# and is captured by backup.sh's staging. This script therefore edits in place
# against a timestamped backup rather than overwriting from a template, and
# restores that backup if anything fails validation.
set -euo pipefail

TARGET=/usr/local/sbin/notify-telegram
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="/root/notify-telegram.backup.$STAMP"

[[ $EUID -eq 0 ]] || { echo "needs root: sudo $0" >&2; exit 1; }
[[ -f $TARGET ]] || { echo "missing $TARGET" >&2; exit 1; }

if grep -q "parse_mode" "$TARGET"; then
  echo "already patched (parse_mode present) — nothing to do"; exit 0
fi

cp -a "$TARGET" "$BACKUP"
echo "→ backup: $BACKUP"

python3 - "$TARGET" <<'PATCH'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()

# --html opt-out of escaping, parsed alongside the existing args.
s = s.replace('set -u', '''set -u

# --html: the caller already produced Telegram HTML (see
# ai-agent-platform/agents/telegram_format.py). Without it we escape, which is
# a no-op for plain prose and the safe default for everything else.
PRE_HTML=0
if [ "${1:-}" = "--html" ]; then PRE_HTML=1; shift; fi''', 1)

old = '''RESP=$(curl -sS --max-time 10 -X POST \\
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \\
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \\
    --data-urlencode "text=${TEXT}" 2>&1)'''

new = '''if [ "$PRE_HTML" -eq 0 ]; then
    # Only & < > matter in HTML mode, and & must go first or it eats the
    # entities the next two substitutions create.
    TEXT=$(printf '%s' "$TEXT" | sed -e 's/&/\\&amp;/g' -e 's/</\\&lt;/g' -e 's/>/\\&gt;/g')
fi

RESP=$(curl -sS --max-time 10 -X POST \\
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \\
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \\
    --data-urlencode "parse_mode=HTML" \\
    --data-urlencode "text=${TEXT}" 2>&1)

# Telegram rejects a malformed entity with 400 and delivers nothing. A pager
# that arrives unformatted beats one that does not arrive, so retry once raw.
if ! printf '%s' "$RESP" | grep -q '"ok":true'; then
    slog "HTML render rejected, retrying plain: ${RESP:0:120}"
    RESP=$(curl -sS --max-time 10 -X POST \\
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \\
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \\
        --data-urlencode "text=${MSG}" 2>&1)
fi'''

if old not in s:
    sys.exit("send block not found — helper differs from what this patch expects")
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
PATCH

if ! bash -n "$TARGET"; then
  echo "patched file fails syntax check — restoring" >&2
  cp -a "$BACKUP" "$TARGET"; exit 1
fi

echo "→ live test send"
if ! "$TARGET" NOTIFY "formatting check: <b>bold</b> and <code>a &lt; b</code> should render"; then
  echo "test send failed — restoring" >&2
  cp -a "$BACKUP" "$TARGET"; exit 1
fi

echo "patched. Backup kept at $BACKUP — remove it once the next few pages look right."
