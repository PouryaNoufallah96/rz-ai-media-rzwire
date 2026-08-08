"""Approved RZWire workspace FAQ corpus."""

_PAIRS = (
    ('workspace', 100, ('rzwire', 'workspace', 'website'), 'What is RZWire?', 'RZWire is a private publishing workspace for sourcing news, routing stories, and creating brand-aware copy and imagery.'),
    ('brands', 110, ('brands', 'six brands', 'media brands'), 'Which brands are available?', 'RZWire contains six brands: MGC Coin, Ranking Platform, Oasis Coin, Jewelry Coin, Industrial Token, and Real Estate Token.'),
    ('mgc', 110, ('mgc', 'meta games coin', 'gaming token'), 'What is MGC Coin?', 'MGC Coin is the gaming-economy brand for utility, rewards, player participation, and connected gaming experiences.'),
    ('ranking', 110, ('ranking', 'ranking platform', 'ranking game'), 'What is Ranking Platform?', 'Ranking Platform is the competition and community brand for rankings, profiles, tournaments, teams, venues, and player achievement.'),
    ('oasis', 110, ('oasis', 'oasis coin', 'rzoasis'), 'What is Oasis Coin?', 'Oasis Coin is the restrained, future-facing ecosystem brand. Planned utility must always be described as planned, not live.'),
    ('jewelry', 110, ('jewelry', 'jewelry coin', 'jewelry token'), 'What is Jewelry Coin?', 'Jewelry Coin connects digital creation, virtual gems, tokenized designs, NFTs, and a planned path toward physical jewelry.'),
    ('industrial', 110, ('industrial', 'industrial token', 'industrial.game'), 'What is Industrial Token?', 'Industrial Token is the BEP-20 industrial ecosystem brand for gamified industrial marketing, smart factories, education, supply-chain transparency, and sustainability-oriented activity.'),
    ('real_estate', 110, ('real estate', 'real estate token', 'realestate', 'real-estate.game'), 'What is Real Estate Token?', 'Real Estate Token is the BEP-20 property ecosystem brand for real-world and digital property experiences, transparent ownership records, fractional participation, and community-led real estate activity.'),
    ('analyze', 90, ('analyze', 'route', 'editorial'), 'How does Analyze work?', 'Analyze scores selected stories for editorial fit and routes suitable cards into the selected brand lanes.'),
    ('preview', 90, ('preview', 'copy', 'image'), 'What is Preview?', 'Preview is where you review copy, generate a brand-styled image, save the card, and prepare it for approval.'),
    ('sources', 90, ('rss', 'telegram sources', 'news sources'), 'Which news sources are used?', 'RZWire keeps the curated RSS websites and Telegram news sources configured in the Multimedia sidebar.'),
    ('local_safety', 120, ('publishing', 'sheets', 'disabled', 'local'), 'Can RZWire publish right now?', 'External posting, scheduled auto-posting, and Google Sheets writes are disabled in the local workspace until the new RZWire integrations are supplied.'),
    ('account', 80, ('account', 'saved cards', 'history'), 'What is Account?', 'Account shows local activity, saved cards, and scheduled items for the current user.'),
)

FAQ_SEEDS = tuple({
    'managedKey': f'{key}:en', 'question': question, 'aliases': [],
    'keywords': list(keywords), 'answer': answer, 'language': 'en', 'priority': priority,
} for key, priority, keywords, question, answer in _PAIRS)
