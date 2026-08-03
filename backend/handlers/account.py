"""Account: activity logging, saved cards, brand keywords, summary aggregation."""
import database

from analytics_brands import get_analytics_brand
from analytics_chart_style import normalize_chart_style
from config import MEDIA_LIST, BATCH_WINDOW, VALID_ACTIONS, EDITORIAL_MODELS, PLAT_RULES
from handlers.sheets import call_apps_script
from datetime import datetime as _datetime, timedelta as _timedelta


def group_activity(rows):
    """rows: list[dict] ordered created_at DESC (most recent first).
    Returns list of batch dicts, most-recent-first."""
    batches = []
    for row in rows:
        ts = _datetime.fromisoformat(row['created_at'])
        last = batches[-1] if batches else None
        same_group = (
            last is not None and
            row['brand'] == last['brand'] and
            row['model_display'] == last['model_display'] and
            (last['_first_ts'] - ts) <= BATCH_WINDOW
        )
        if same_group:
            last['count'] += 1
            last['platforms'].add(row['platform'])
            last['actions'].add(row['action'])
        else:
            batches.append({
                'brand': row['brand'], 'model_display': row['model_display'],
                'count': 1, 'platforms': {row['platform']}, 'actions': {row['action']},
                'headline': row['headline'], 'created_at': row['created_at'], '_first_ts': ts,
            })
    return [{
        'brand': b['brand'], 'modelDisplay': b['model_display'], 'count': b['count'],
        'platforms': sorted(b['platforms']), 'actions': sorted(b['actions']),
        'headline': b['headline'], 'createdAt': b['created_at'],
    } for b in batches]


def build_account_summary(user_id):
    posts_generated = database.count_activity(user_id)
    scheduled       = database.count_activity(user_id, action='scheduled')
    saved_count     = database.count_saved_cards(user_id, status='saved')

    brand_stats = database.get_brand_stats(user_id)
    posts_by_brand = {b: brand_stats.get(b, {'generated': 0, 'scheduled': 0}) for b in MEDIA_LIST}

    recent_rows = database.get_recent_activity(user_id, limit=200)
    activity = group_activity(recent_rows)[:20]

    return {
        'stats': {'postsGenerated': posts_generated, 'scheduled': scheduled, 'saved': saved_count},
        'postsByBrand': posts_by_brand,
        'activity': activity,
        'recentKeywords': database.get_recent_keywords(user_id, limit=12),
    }


def handle_log_action(user_id, body):
    brand    = (body.get('brand') or '').strip()
    platform = (body.get('platform') or '').strip()
    model    = (body.get('modelDisplay') or '').strip()
    headline = (body.get('headline') or '').strip()
    action   = (body.get('action') or '').strip()
    if not brand or not platform or not action:
        raise ValueError('brand, platform, and action are required')
    if action not in VALID_ACTIONS:
        raise ValueError(f'Invalid action: {action}')
    database.log_activity(user_id, brand, platform, model, headline, action)
    return {'ok': True}


def handle_log_keywords(user_id, body):
    topics = body.get('topics', '')
    brands = body.get('brands', [])
    keywords = [k.strip() for k in topics.split(',') if k.strip()]
    for brand in (brands or ['']):
        database.log_keywords(user_id, keywords, brand)
    return {'ok': True, 'logged': len(keywords)}


def handle_brand_keywords(user_id, brands_param):
    brands = [b.strip() for b in brands_param.split(',') if b.strip()]
    if not brands:
        return {'keywords': []}
    return {'keywords': database.get_brand_keywords(user_id, brands)}


def handle_get_analytics_chart_default(user_id, brand_id):
    brand = get_analytics_brand(str(brand_id or '').strip().lower())
    saved = database.get_analytics_chart_default(user_id, brand['id'])
    if not saved:
        return {'brandId': brand['id'], 'style': None, 'updatedAt': None}
    try:
        style = normalize_chart_style(saved.get('style'))
    except ValueError:
        style = None
    return {'brandId': brand['id'], 'style': style, 'updatedAt': saved.get('updatedAt')}


def handle_save_analytics_chart_default(user_id, body):
    brand = get_analytics_brand(str(body.get('brandId') or '').strip().lower())
    if not isinstance(body.get('style'), dict):
        raise ValueError('style is required and must be an object')
    style = normalize_chart_style(body.get('style'))
    saved = database.save_analytics_chart_default(user_id, brand['id'], style)
    return {'ok': True, 'brandId': brand['id'], **saved}


def handle_saved_discard(user_id, body):
    saved_id = body.get('id')
    if not saved_id:
        raise ValueError('id is required')
    if not database.update_saved_card_status(saved_id, user_id, 'discarded'):
        raise ValueError('Saved card not found')
    return {'ok': True}


def handle_saved_update(user_id, body):
    saved_id = body.get('id')
    if not saved_id:
        raise ValueError('id is required')

    brand = (body.get('media') or body.get('brand') or '').strip()
    platform = (body.get('platform') or '').strip()
    model_key = (body.get('modelKey') or '').strip()

    if brand and brand not in MEDIA_LIST:
        raise ValueError(f'Unknown media brand: {brand}')
    if platform and platform not in PLAT_RULES:
        raise ValueError(f'Unknown platform: {platform}')
    if model_key and model_key not in EDITORIAL_MODELS:
        raise ValueError(f'Unknown editorial model: {model_key}')

    updated = database.update_saved_card(saved_id, user_id, body)
    if not updated:
        raise ValueError('Saved card not found')
    return {'ok': True, 'card': updated}


def handle_saved_confirm_schedule(user_id, body):
    saved_id   = body.get('id')
    sched_date = body.get('scheduledDate')
    sched_time = body.get('scheduledTime')
    if not saved_id or not sched_date or not sched_time:
        raise ValueError('id, scheduledDate, and scheduledTime are required')

    card = database.get_saved_card(saved_id, user_id)
    if not card:
        raise ValueError('Saved card not found')

    copy = body.get('copy') or card['copy']
    hashtags = body.get('hashtags') or card['hashtags']
    headline = (body.get('headline') or card['headline']).strip()
    brand = (body.get('media') or body.get('brand') or card['brand']).strip()
    platform = (body.get('platform') or card['platform']).strip()
    model_display = (body.get('modelDisplay') or card['model_display'] or '').strip()

    call_apps_script({
        'action': 'schedule', 'id': card['card_id'], 'title': headline,
        'source': card['source'], 'sourceUrl': card['source_link'] or '',
        'mediaBrand': brand, 'platform': platform, 'copy': copy,
        'hashtags': hashtags, 'sentiment': card['sentiment'],
        'fitScore': card['suitability'], 'impactScore': card['impact'], 'viralityScore': card['virality'],
        'scheduledDate': sched_date, 'scheduledTime': sched_time,
    })

    database.log_activity(user_id, brand, platform, model_display, headline, 'scheduled')
    database.update_saved_card_status(saved_id, user_id, 'scheduled')
    return {'ok': True}
