"""Scheduling: CRUD for scheduled posts + the background auto-post loop."""
import time
import sys

import database
from config import PUBLISHING_ENABLED, SCHEDULER_INTERVAL_SEC
from datetime import datetime as _datetime, timezone as _timezone
from server_utils import _parse_iso_utc
from handlers.social import handle_telegram_post, handle_twitter_post
from handlers.sheets import call_apps_script


def handle_schedule_create(user_id, body):
    if not PUBLISHING_ENABLED:
        raise ValueError('RZWire publishing is disabled; scheduling will be available after integration setup')
    scheduled_at = body.get('scheduledAt')
    if not scheduled_at:
        raise ValueError('scheduledAt is required')
    try:
        dt = _parse_iso_utc(scheduled_at)
    except ValueError:
        raise ValueError('Invalid scheduledAt')
    data = {**body, 'scheduledAt': dt.isoformat()}
    post_id = database.create_scheduled_post(user_id, data)
    return {'ok': True, 'id': post_id}


def handle_schedule_list(user_id):
    posts = database.get_scheduled_posts(user_id)
    for p in posts:
        p['has_image'] = bool(p.pop('image_b64', None))
    return {'posts': posts}


def handle_schedule_cancel(user_id, body):
    post_id = body.get('id')
    if not post_id:
        raise ValueError('id is required')
    row = database.cancel_scheduled_post(post_id, user_id)
    if not row:
        raise ValueError('Scheduled post not found or already processed')
    if row.get('saved_card_id'):
        database.update_saved_card_status(row['saved_card_id'], user_id, 'saved')
    return {'ok': True}


def handle_schedule_reschedule(user_id, body):
    post_id = body.get('id')
    scheduled_at = body.get('scheduledAt')
    if not post_id or not scheduled_at:
        raise ValueError('id and scheduledAt are required')
    try:
        dt = _parse_iso_utc(scheduled_at)
    except ValueError:
        raise ValueError('Invalid scheduledAt')
    if not database.reschedule_scheduled_post(post_id, user_id, dt.isoformat()):
        raise ValueError('Scheduled post not found or already processed')
    return {'ok': True}

# ── Background scheduler (auto-posts scheduled X/Telegram posts) ───────────────
def execute_scheduled_post(row):
    platform = row['platform']
    image_b64 = row.get('image_b64') or ''
    hashtags = row.get('hashtags') or []
    try:
        if platform == 'Telegram':
            handle_telegram_post({
                'imageB64': image_b64, 'headline': row['headline'],
                'copy': row.get('copy') or '', 'hashtags': hashtags,
                'link': row.get('source_link') or '', 'mediaBrand': row.get('brand') or '',
            })
        elif platform == 'X':
            handle_twitter_post({
                'imageB64': image_b64, 'copy': row.get('copy') or '',
                'hashtags': hashtags, 'platform': platform, 'mediaBrand': row['brand'],
            })
        else:
            raise ValueError(f'Auto-posting not supported for platform {platform}')

        if image_b64 or row.get('image_url'):
            try:
                call_apps_script({
                    'action': 'approve', 'id': row['card_id'], 'title': row['headline'],
                    'source': row.get('source') or '', 'sourceUrl': row.get('source_link') or '',
                    'mediaBrand': row['brand'], 'platform': platform, 'copy': row.get('copy') or '',
                    'hashtags': hashtags, 'sentiment': row.get('sentiment') or '',
                    'fitScore': row.get('suitability'), 'impactScore': row.get('impact'),
                    'viralityScore': row.get('virality'),
                    'imageStatus': 'Image Approved', 'imageUrl': row.get('image_url') or '',
                })
            except Exception as e:
                # Sheet update is best-effort — the post itself already succeeded —
                # but log it so a stale Sheet row is debuggable later.
                print(f'[scheduler] Sheet update failed for post {row["id"]}: {e}', file=sys.stderr)

        database.log_activity(row['user_id'], row['brand'], platform,
                               row.get('model_display') or '', row['headline'], 'published')
        database.mark_scheduled_post(row['id'], 'posted')
    except Exception as e:
        database.mark_scheduled_post(row['id'], 'failed', error=str(e)[:500])


def run_scheduler_loop():
    # Posts whose time passed while the server was offline still fire on the
    # next poll after restart ("fire late", never silently skipped) — there is
    # no grace-window cutoff. A "failed" post is terminal (no automatic retry);
    # the user must re-schedule it manually.
    while True:
        try:
            if PUBLISHING_ENABLED:
                for row in database.get_due_scheduled_posts(_datetime.now(_timezone.utc).isoformat()):
                    execute_scheduled_post(row)
        except Exception as e:
            print(f'[scheduler] {e}', file=sys.stderr)
        time.sleep(SCHEDULER_INTERVAL_SEC)
