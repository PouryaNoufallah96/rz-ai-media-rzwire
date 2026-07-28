"""Batch translation for final cards displayed in the Persian interface."""
import re

from llm import openrouter_chat


_TRANSLATION_MODEL_ID = 'google/gemini-2.5-flash-lite'
_PROTECTED_NAMES = (
    'RZWire', 'MGC Coin', 'Meta Games Coin', 'Ranking Platform', 'Ranking.Game',
    'Oasis Coin', 'OASIS', 'RZOASIS', 'Jewelry Coin', 'Jewelry Token', 'CoinMarketCap',
    'Bitcoin', 'Ethereum', 'Tether', 'Solana', 'Cardano', 'Dogecoin', 'Polkadot',
    'Avalanche', 'Chainlink', 'Polygon', 'Litecoin', 'Arbitrum', 'Optimism',
    'Uniswap', 'MakerDAO', 'MetaMask', 'Telegram', 'Binance', 'Coinbase', 'Kraken',
    'Bybit', 'Bitget', 'OpenAI', 'Gemini', 'DeepSeek',
)
_PROTECTED_RE = re.compile(
    r'https?://\S+|@[A-Za-z0-9_]+|#[A-Za-z][A-Za-z0-9_]*|\$[A-Za-z][A-Za-z0-9]*|'
    r'\b[A-Z][A-Z0-9.-]{1,}\b|\b(?i:' +
    '|'.join(re.escape(name) for name in sorted(_PROTECTED_NAMES, key=len, reverse=True)) +
    r')\b',
)


def _placeholder(index):
    letters = ''
    while True:
        index, remainder = divmod(index, 26)
        letters = chr(65 + remainder) + letters
        if index == 0:
            return f'CRKEEP{letters}TOKEN'
        index -= 1


def _protect_terms(text, replacements):
    def replace(match):
        token = _placeholder(len(replacements))
        replacements[token] = match.group(0)
        return token

    return _PROTECTED_RE.sub(replace, text or '')


def _restore_terms(text, replacements):
    restored = text or ''
    for token, original in replacements.items():
        restored = restored.replace(token, original)
    return restored


def handle_translate_cards(body):
    articles = body.get('articles') or []
    if body.get('language') != 'fa' or not articles:
        return {'articles': articles}

    replacements = {}
    compact = []
    for index, item in enumerate(articles):
        compact.append({
            'index': index,
            'title': _protect_terms(item.get('title', ''), replacements),
            'desc': _protect_terms(item.get('desc', item.get('description', '')), replacements),
        })
    system = (
        'Translate each title and desc into fluent Persian. Use Persian digits and RTL-friendly punctuation. '
        'Keep crypto tickers, coin, project, brand, and source names, and URLs in their original Latin script. '
        'For example, write Bitcoin, Ethereum, BNB, and OKX exactly as given; never transliterate these names. '
        'Copy every CRKEEP...TOKEN placeholder exactly without changing or removing it. '
        'Return ONLY JSON in this exact shape: {"items":[{"index":0,"title":"...","desc":"..."}]}.'
    )
    result = openrouter_chat(
        _TRANSLATION_MODEL_ID,
        [{'role': 'system', 'content': system}, {'role': 'user', 'content': str(compact)}],
        temperature=0.2,
        max_tokens=4000,
    )
    translated = result.get('items', []) if isinstance(result, dict) else []
    by_index = {item.get('index'): item for item in translated if isinstance(item, dict)}
    output = []
    for index, article in enumerate(articles):
        item = by_index.get(index, {})
        title = _restore_terms(item.get('title'), replacements) or article.get('title', '')
        desc = (_restore_terms(item.get('desc'), replacements) or
                article.get('desc', article.get('description', '')))
        output.append({**article, 'title': title, 'desc': desc})
    return {'articles': output}
