"""Local scope policy for the in-app assistant.

Rejected requests are answered deterministically before OpenRouter is called.
This keeps the assistant limited to RZWire knowledge and avoids spending
tokens on unrelated or unsupported requests.
"""
import re


_PERSIAN_RE = re.compile(r'[\u0600-\u06ff]')

# These are intentionally short, anchored messages.  A greeting such as
# "Hi, how do I schedule a post?" is not caught here and will continue into
# normal website knowledge retrieval.
_SMALL_TALK_RULES = (
    (
        'greeting',
        re.compile(
            r'^\s*(?:hi|hello|hey|hello there|hi there|good morning|'
            r'good afternoon|good evening|سلام|درود)\s*[!.؟?]*\s*$',
            re.IGNORECASE,
        ),
    ),
    (
        'how_are_you',
        re.compile(
            r'^\s*(?:how are you|how are things|how(?:\'| a)?re you doing|'
            r'what(?:\'| i)?s up|خوبی|چطوری|حالت چطوره)\s*[!.؟?]*\s*$',
            re.IGNORECASE,
        ),
    ),
    (
        'thanks',
        re.compile(
            r'^\s*(?:thanks|thank you|thanks a lot|thank you so much|'
            r'merci|ممنون|مرسی|سپاس)\s*[!.؟?]*\s*$',
            re.IGNORECASE,
        ),
    ),
    (
        'goodbye',
        re.compile(
            r'^\s*(?:bye|goodbye|see you|see you later|good night|'
            r'خداحافظ|فعلا|شب بخیر)\s*[!.؟?]*\s*$',
            re.IGNORECASE,
        ),
    ),
)

_IN_SCOPE_RE = re.compile(
    r"\b(?:rzwire|mgc|meta\s*games\s*coin|metagamescoin|ranking(?:\.game|\s*platform)?|"
    r"oasis\s*(?:coin|token)|rzoasis|jewel(?:ry|lery)\s*(?:coin|token|game)|brand|brand bible|media|"
    r"workspace|website|sidebar|multimedia|account|chatbot|assistant|chat history|faq|answer cache|article|story|news card|card|"
    r"headline|caption|hashtag|social copy|copy|image|visual|tone|audience|"
    r"content pillar|analy[sz]e|editorial|filter|route|lane|preview|save|saved|"
    r"schedule|publish|telegram|twitter|instagram|rss|source|model|translate|"
    r"translation|language|google sheet|activity|keyword)\b|"
    r"(?:رسانه|وب.?سایت|سایت|برند|خبر|مقاله|کارت|تیتر|کپشن|هشتگ|تصویر|"
    r"تحلیل|فیلتر|انتخاب|منبع|مدل|ترجمه|زبان|ذخیره|زمان.?بندی|انتشار|"
    r"تلگرام|اینستاگرام|توییتر|اکانت|حساب)",
    re.IGNORECASE,
)

_FOLLOW_UP_RE = re.compile(
    r"^(?:tell me more|explain more|why|how|what about (?:it|this|that|them|the other one)|"
    r"which one|compare them|yes|no|continue|go on|more details|"
    r"بیشتر توضیح بده|چرا|چطور|کدام|مقایسه کن|ادامه بده)[?.!\s]*$",
    re.IGNORECASE,
)

_SELECTION_REFERENCE_RE = re.compile(
    r"\b(?:what (?:is|does|are) (?:this|that|it|they|the (?:brand|media))|"
    r"what should i know|who (?:is|are) (?:they|this|that)|tell me about (?:it|this|that|them)|explain (?:it|this|that)|compare|"
    r"what do (?:they|you) do|which (?:brand|media)|this brand|these brands)\b|"
    r"(?:این برند|این رسانه|اینها|درباره|مقایسه|چه کاری|کدام برند)",
    re.IGNORECASE,
)

_CAPABILITY_QUESTION_RE = re.compile(
    r"\b(?:can|could|does|do|will|is it possible|are you able|support|allow)\b.*"
    r"\b(?:you|chatbot|assistant|website|site|workspace|rzwire)\b|"
    r"\b(?:can|could)\s+(?:you|it|the (?:site|website))\b|"
    r"(?:آیا|میشه|می.?توانی|می.?تونه).*(?:چت.?بات|دستیار|سایت|وب.?سایت)",
    re.IGNORECASE,
)

_CHATBOT_SCOPE_QUESTION_RE = re.compile(
    r"\b(?:what can (?:the )?(?:rzwire )?(?:chatbot|assistant) (?:do|help with)|"
    r"how can (?:the )?(?:chatbot|assistant) help|what can i ask (?:the )?(?:chatbot|assistant))\b|"
    r"(?:چت.?بات چه کاری انجام می.?دهد|ربات چه کمکی می.?کند|از ربات چه سوالی می.?توانم بپرسم)",
    re.IGNORECASE,
)

_SUPPORTED_CAPABILITY_RE = re.compile(
    r"\b(?:analy[sz]e|filter|route|import|rss|news source|telegram source|"
    r"generate|create|edit|translate|save|schedule|publish|post|sync|upload image|"
    r"copy|caption|headline|hashtag|image|preview|account stat|activity|saved card|"
    r"google sheet|telegram|twitter|instagram content)\b|"
    r"(?:تحلیل|فیلتر|مسیردهی|ورود خبر|منبع خبر|تولید|ساخت|ویرایش|ترجمه|ذخیره|"
    r"زمان.?بندی|انتشار|کپشن|تیتر|هشتگ|تصویر|آمار حساب|گوگل شیت|تلگرام|توییتر)",
    re.IGNORECASE,
)

_BRAND_SCOPE_RE = re.compile(
    r"\b(?:mgc|meta\s*games\s*coin|metagamescoin|ranking(?:\.game|\s*platform)?|"
    r"oasis\s*(?:coin|token)|rzoasis|jewel(?:ry|lery)\s*(?:coin|token|game)|brand bible|brand tone|"
    r"brand audience|content pillar|media brand)\b|"
    r"(?:برند|لحن برند|مخاطب برند|رسانه)",
    re.IGNORECASE,
)

_DIRECT_INSTAGRAM_RE = re.compile(
    r"(?:\b(?:publish|send|auto.?post|post directly|connect)\b.*\binstagram\b|"
    r"\binstagram\b.*\b(?:publish|send|auto.?post|post directly|connect)\b|"
    r"(?:انتشار مستقیم|ارسال|اتصال).*(?:اینستاگرام)|"
    r"(?:اینستاگرام).*(?:انتشار مستقیم|ارسال|اتصال))",
    re.IGNORECASE,
)

_UNSUPPORTED_RULES = (
    (
        'external_platform',
        re.compile(r"\b(?:linkedin|facebook|tiktok|youtube|whatsapp|discord|reddit|"
                   r"pinterest|snapchat|email|e-mail|sms|newsletter)\b|"
                   r"(?:لینکدین|فیسبوک|تیک.?تاک|یوتیوب|واتساپ|دیسکورد|ایمیل|پیامک)", re.IGNORECASE),
    ),
    (
        'financial_action',
        re.compile(r"\b(?:buy|sell|trade|swap|transfer|withdraw|deposit|pay)\b.*"
                   r"\b(?:coin|token|crypto|bitcoin|ethereum|money|funds?)\b|"
                   r"\b(?:connect|import)\b.*\bwallet\b|"
                   r"(?:خرید|فروش|معامله|پرداخت|برداشت|واریز|اتصال).*(?:ارز|توکن|بیت.?کوین|کیف پول)", re.IGNORECASE),
    ),
    (
        'external_browsing',
        re.compile(r"\b(?:browse|search|look up|google|check)\b.*\b(?:internet|web|online|live price|current price)\b|"
                   r"(?:جستجو|سرچ).*(?:اینترنت|وب|قیمت لحظه)", re.IGNORECASE),
    ),
    (
        'unsupported_output',
        re.compile(r"\b(?:export|download|create|generate)\b.*\b(?:pdf|powerpoint|ppt|excel file|video|reel|audio|music)\b|"
                   r"(?:استودیو)|(?:خروجی|دانلود|ساخت|تولید).*(?:پی.?دی.?اف|پاورپوینت|ویدیو|ریلز|صدا|موسیقی)", re.IGNORECASE),
    ),
    (
        'account_operation',
        re.compile(r"\b(?:delete|create|disable)\b.*\baccount\b|\breset\b.*\bpassword\b|"
                   r"(?:حذف|ساخت|غیرفعال).*(?:حساب|اکانت)|(?:ریست|بازیابی).*(?:رمز)", re.IGNORECASE),
    ),
)


def _language(message):
    return 'fa' if _PERSIAN_RE.search(message or '') else 'en'


def _reply(kind, message, reason=None):
    persian = _language(message) == 'fa'
    if kind == 'small_talk':
        replies = {
            'greeting': (
                'سلام! من دستیار RZWire هستم. امروز چطور می‌توانم کمکتان کنم؟'
                if persian else
                'Hi! I’m the RZWire assistant. How can I help you today?'
            ),
            'how_are_you': (
                'خوبم، ممنون! آماده‌ام درباره RZWire و کارهای وب‌سایت کمک کنم.'
                if persian else
                'I’m doing well, thanks! I’m ready to help with RZWire and the website.'
            ),
            'thanks': (
                'خواهش می‌کنم! هر زمان آماده بودید، سؤال بعدی‌تان را بپرسید.'
                if persian else
                'You’re welcome! Ask me anything about the website whenever you’re ready.'
            ),
            'goodbye': (
                'خداحافظ! هر زمان نیاز داشتید، من اینجا هستم.'
                if persian else
                'Goodbye! I’ll be here whenever you need help.'
            ),
        }
        return replies[reason]
    if kind == 'unsupported':
        if reason == 'instagram_publish':
            return (
                'RZWire می‌تواند محتوای اینستاگرام را آماده کند، اما در حال حاضر انتشار مستقیم در اینستاگرام را انجام نمی‌دهد.'
                if persian else
                'RZWire can prepare Instagram content, but it cannot publish directly to Instagram.'
            )
        return (
            'این وب‌سایت در حال حاضر این کار را انجام نمی‌دهد. قابلیت‌های موجود شامل تحلیل و مسیردهی خبر، تولید متن و تصویر، ترجمه کارت‌ها، ذخیره یا زمان‌بندی محتوا و انتشار در تلگرام یا X است.'
            if persian else
            'This website cannot do that currently. Available functions include analyzing and routing stories, generating copy and images, translating cards, saving or scheduling content, and publishing to Telegram or X.'
        )
    return (
        'من فقط درباره RZWire، چهار برند آن، کارت خبر فعال و قابلیت‌های موجود در این وب‌سایت پاسخ می‌دهم.'
        if persian else
        'I can only answer questions about RZWire, its four brands, the active news card, and functions available in this website.'
    )


def _previous_reply_was_rejection(history):
    if not history:
        return False
    previous = history[-1].get('content', '')
    starts = (
        'I can only answer questions about RZWire',
        'This website cannot do that currently',
        'RZWire can prepare Instagram content',
        'من فقط درباره RZWire',
        'این وب‌سایت در حال حاضر این کار را انجام نمی‌دهد',
        'RZWire می‌تواند محتوای اینستاگرام',
    )
    return previous.startswith(starts)


def classify(message, history=None, selected_media=None, has_active_card=False,
             reply_message=None):
    """Return a local policy decision: allow, small_talk, unsupported, or unrelated."""
    history = history or []
    selected_media = selected_media or []
    text = (message or '').strip()
    reply_text = reply_message if reply_message is not None else text

    if _DIRECT_INSTAGRAM_RE.search(text):
        return {'kind': 'unsupported', 'reason': 'instagram_publish', 'reply': _reply('unsupported', reply_text, 'instagram_publish')}

    for reason, pattern in _UNSUPPORTED_RULES:
        if pattern.search(text):
            return {'kind': 'unsupported', 'reason': reason, 'reply': _reply('unsupported', reply_text, reason)}

    for reason, pattern in _SMALL_TALK_RULES:
        if pattern.search(text):
            return {'kind': 'small_talk', 'reason': reason, 'reply': _reply('small_talk', reply_text, reason)}

    if _CHATBOT_SCOPE_QUESTION_RE.search(text):
        return {'kind': 'allow', 'reason': 'chatbot_scope_question', 'reply': None}

    if _CAPABILITY_QUESTION_RE.search(text):
        if _SUPPORTED_CAPABILITY_RE.search(text) or _BRAND_SCOPE_RE.search(text):
            return {'kind': 'allow', 'reason': 'documented_capability', 'reply': None}
        return {'kind': 'unsupported', 'reason': 'unknown_capability', 'reply': _reply('unsupported', reply_text, 'unknown_capability')}

    if _IN_SCOPE_RE.search(text):
        return {'kind': 'allow', 'reason': 'rzwire_scope', 'reply': None}

    if has_active_card and (_FOLLOW_UP_RE.search(text) or _SELECTION_REFERENCE_RE.search(text)):
        return {'kind': 'allow', 'reason': 'active_card_follow_up', 'reply': None}

    if selected_media and (_FOLLOW_UP_RE.search(text) or _SELECTION_REFERENCE_RE.search(text)):
        return {'kind': 'allow', 'reason': 'media_selection_follow_up', 'reply': None}

    if history and _FOLLOW_UP_RE.search(text) and not _previous_reply_was_rejection(history):
        return {'kind': 'allow', 'reason': 'conversation_follow_up', 'reply': None}

    return {'kind': 'unrelated', 'reason': 'outside_scope', 'reply': _reply('unrelated', reply_text)}
