import { create } from 'zustand'

const STORAGE_KEY = 'rzwire-language'

export const FA = {
  'Multi Media': 'چندرسانه‌ای',
  'About Us': 'درباره ما',
  'Account': 'حساب کاربری',
  'English': 'English',
  'Persian': 'فارسی',
  'Settings': 'تنظیمات',
  'Log Out': 'خروج',
  'Posts Generated': 'پست‌های تولیدشده',
  'Scheduled': 'زمان‌بندی‌شده',
  'Saved': 'ذخیره‌شده',
  'Posts by Media Brand': 'پست‌ها بر اساس برند رسانه',
  'Activity History': 'تاریخچه فعالیت',
  'Recent Keywords': 'کلیدواژه‌های اخیر',
  'Scheduled Posts': 'پست‌های زمان‌بندی‌شده',
  'Saved for Later': 'ذخیره برای بعد',
  'Member since': 'عضو از',
  'Sign In': 'ورود',
  'Welcome back': 'خوش آمدید',
  'Username': 'نام کاربری',
  'Password': 'رمز عبور',
  'Remember me': 'مرا به خاطر بسپار',
  'Forgot password?': 'رمز عبور را فراموش کرده‌اید؟',
  'Analyze & Route News': 'تحلیل و مسیردهی اخبار',
  'Telegram News': 'اخبار تلگرام',
  'Latest news': 'جدیدترین اخبار',
  'By view count': 'بر اساس بازدید',
  'By matching keywords': 'بر اساس کلیدواژه‌های مشابه',
  'Most views per source': 'بیشترین بازدید از هر منبع',
  'Newest per source': 'جدیدترین از هر منبع',
  'How many top articles?': 'تعداد خبرهای برتر',
  'Topics / Keywords': 'موضوعات / کلیدواژه‌ها',
  'Time Range': 'بازه زمانی',
  'Filter Engine': 'موتور فیلتر',
  'AI Editorial Models': 'مدل‌های تحریریه هوش مصنوعی',
  'Source Enrichment': 'غنی‌سازی منبع',
  'Select Media': 'انتخاب رسانه',
  'Destination Platforms': 'پلتفرم‌های مقصد',
  'Select Source': 'انتخاب منبع',
  'Approve': 'تایید',
  'Schedule': 'زمان‌بندی',
  'Save for Later': 'ذخیره برای بعد',
  'Generate Image': 'تولید تصویر',
  'Generate Copy': 'تولید متن',
  'Cancel': 'لغو',
  'Edit': 'ویرایش',
  'Pending': 'در انتظار',
  'Posted': 'منتشرشده',
  'Failed': 'ناموفق',
  'Ready': 'آماده',
  'Needs Image': 'نیازمند تصویر',
  'Approved': 'تاییدشده',
  'Published': 'منتشرشده',
  'Image': 'تصویر',
  'Fit': 'تناسب',
  'No activity yet': 'هنوز فعالیتی وجود ندارد',
  'Nothing saved yet': 'هنوز چیزی ذخیره نشده است',
  'Nothing scheduled': 'زمان‌بندی‌ای وجود ندارد',
  'Select a saved card to preview': 'یک کارت ذخیره‌شده را برای پیش‌نمایش انتخاب کنید',
  'Open Dashboard': 'باز کردن داشبورد',
  'AI-Powered Crypto Journalism': 'روزنامه‌نگاری رمزارز با هوش مصنوعی',
  'All rights reserved.': 'تمامی حقوق محفوظ است.',
  'Use website sources too?': 'از منابع وب هم استفاده شود؟',
  'Telegram only': 'فقط تلگرام',
  'Yes, use both': 'بله، از هر دو استفاده کن',
  'Route the right news to the right media brand and platform.': 'خبر مناسب را به برند رسانه‌ای و پلتفرم مناسب هدایت کنید.',
  'Token Access · BNB Chain · Retail': 'دسترسی به توکن · زنجیره BNB · کاربران عمومی',
  'Luxury · Web3 · Aspirational': 'لوکس · وب ۳ · الهام‌بخش',
  'General Crypto News · Full Spectrum': 'اخبار عمومی رمزارز · پوشش کامل',
  'Security · DeFi Protection · Risk': 'امنیت · حفاظت دیفای · ریسک',
  'Promo Copy': 'متن تبلیغاتی',
  'Promo mode': 'حالت تبلیغاتی',
  'Promo mode — sources not used.': 'در حالت تبلیغاتی از منابع خبری استفاده نمی‌شود.',
  'Creates columns. Drag news cards into them after analysis.': 'ستون‌ها را ایجاد می‌کند. پس از تحلیل، کارت‌های خبر را به ستون موردنظر بکشید.',
  'Short viral · 280 chars': 'کوتاه و پربازدید · ۲۸۰ نویسه',
  'Summaries · takeaways': 'خلاصه‌ها · نکات کلیدی',
  'Visual captions · carousel': 'کپشن تصویری · پست اسلایدی',
  'Do you want to use Telegram news too?': 'آیا می‌خواهید از اخبار تلگرام هم استفاده کنید؟',
  'Public channel posts ranked by views or keywords': 'پست‌های کانال‌های عمومی بر اساس بازدید یا کلیدواژه رتبه‌بندی می‌شوند',
  'How do you want to sort the news?': 'اخبار چگونه مرتب شوند؟',
  'Type keyword, press Enter…': 'کلیدواژه را بنویسید و Enter را بزنید…',
  'Telegram-only mode: website sources are off.': 'در حالت فقط تلگرام، منابع وب غیرفعال هستند.',
  'Telegram-only mode: keyword matching ranks the posts.': 'در حالت فقط تلگرام، پست‌ها با تطبیق کلیدواژه رتبه‌بندی می‌شوند.',
  'Promo mode: no filtering needed.': 'در حالت تبلیغاتی نیازی به فیلتر نیست.',
  'Pre-Process': 'پیش‌پردازش',
  'Test Version': 'نسخه آزمایشی',
  'Local ML model · no API cost': 'مدل یادگیری ماشین محلی · بدون هزینه API',
  'text-embedding-3-small · backend': 'text-embedding-3-small · سمت سرور',
  'DeepSeek V4 Flash · routing AI': 'DeepSeek V4 Flash · هوش مصنوعی مسیردهی',
  'Verify API + models · minimal tokens': 'بررسی API و مدل‌ها · کمترین مصرف توکن',
  'Best general-purpose editorial AI': 'بهترین هوش مصنوعی عمومی برای تحریریه',
  'Strong reasoning · multimodal': 'استدلال قدرتمند · چندوجهی',
  'Top reasoning benchmark score': 'برترین امتیاز معیارهای استدلال',
  'Fast · cost-efficient · strong reasoning': 'سریع · مقرون‌به‌صرفه · استدلال قدرتمند',
  'Choose one model for copy generation after a Telegram card is routed.': 'برای تولید متن پس از مسیردهی کارت تلگرام، یک مدل انتخاب کنید.',
  'Choose 1–5 models. Each picks 5 articles per brand independently.': '۱ تا ۵ مدل انتخاب کنید. هر مدل به‌طور مستقل ۵ مقاله برای هر برند انتخاب می‌کند.',
  'Use this model to generate copy after a Telegram card is routed.': 'پس از مسیردهی کارت تلگرام، با این مدل متن تولید کنید.',
  'Fetch & summarize source articles for richer AI picks (+4-7s)': 'دریافت و خلاصه‌سازی مقاله‌های منبع برای انتخاب دقیق‌تر هوش مصنوعی (۴ تا ۷ ثانیه بیشتر)',
  'Choose both to keep RSS website news alongside Telegram. Choose Telegram only to search Telegram posts by keywords and pick one AI model for copy after routing a card.': 'برای نگه‌داشتن اخبار وب‌سایت در کنار تلگرام، هر دو را انتخاب کنید. برای جست‌وجوی پست‌های تلگرام با کلیدواژه و انتخاب یک مدل تولید متن، فقط تلگرام را انتخاب کنید.',
  'Analyzing...': 'در حال تحلیل…',
  'Legend': 'راهنما',
  'Ready to review': 'آماده بررسی',
  'Image required': 'نیازمند تصویر',
  'Ready to publish': 'آماده انتشار',
  'Queued to publish': 'در صف انتشار',
  'No articles': 'مقاله‌ای وجود ندارد',
  'No stories routed here yet': 'هنوز خبری به این ستون هدایت نشده است',
  'No Telegram posts': 'پستی از تلگرام وجود ندارد',
  'stories': 'خبر',
  'Select media brands, platforms, and sources — then click': 'برندهای رسانه‌ای، پلتفرم‌ها و منابع را انتخاب کنید، سپس روی',
  'AI assigns each story to the right brand and format. Drag cards between lanes to reassign.': 'هوش مصنوعی هر خبر را به برند و قالب مناسب اختصاص می‌دهد. برای تغییر مسیر، کارت‌ها را بین ستون‌ها جابه‌جا کنید.',
  'shortlisted': 'منتخب',
  'AI editors chose from': 'ویرایشگر هوش مصنوعی انتخاب کرد از',
  'fetched': 'دریافت‌شده',
  'rejected': 'ردشده',
  'too old': 'بیش‌ازحد قدیمی',
  'View Filtering Report': 'مشاهده گزارش فیلتر',
  'Retarget Saved Article': 'تغییر مسیر مقاله ذخیره‌شده',
  'Media': 'رسانه',
  'Platform': 'پلتفرم',
  'AI Editor': 'ویرایشگر هوش مصنوعی',
  'Generate New Copy': 'تولید متن جدید',
  'Why this media brand?': 'چرا این برند رسانه‌ای؟',
  'Why this platform?': 'چرا این پلتفرم؟',
  'Generated Copy': 'متن تولیدشده',
  'Generating 3 platform-specific variants — please wait…': 'در حال تولید ۳ نسخه مخصوص پلتفرم؛ لطفاً صبر کنید…',
  'Variants — pick one': 'نسخه‌ها — یکی را انتخاب کنید',
  'Status:': 'وضعیت:',
  'Confirm': 'تأیید',
  'Confirm Schedule': 'تأیید زمان‌بندی',
  'Discard': 'حذف',
  'Need Image': 'نیاز به تصویر',
  'Hide': 'پنهان کردن',
  'Image Direction': 'راهنمای تصویر',
  '(optional)': '(اختیاری)',
  'Describe what you want in the image… e.g. show the wolf mascot, use a comparison table layout': 'تصویر موردنظر را توضیح دهید؛ برای مثال نمایش نماد گرگ یا استفاده از جدول مقایسه',
  'Reference Images': 'تصاویر مرجع',
  '(optional, max 3)': '(اختیاری، حداکثر ۳ تصویر)',
  'Add Images': 'افزودن تصاویر',
  'Image Generation Model': 'مدل تولید تصویر',
  'Create Image': 'ساخت تصویر',
  'Generating...': 'در حال تولید…',
  'Regenerate': 'تولید دوباره',
  'Download': 'دانلود',
  'Show AI Brief': 'نمایش دستورالعمل هوش مصنوعی',
  'Hide AI Brief': 'پنهان کردن دستورالعمل هوش مصنوعی',
  'Visual Brief (JSON)': 'دستورالعمل بصری (JSON)',
  'Assembled Prompt': 'پرامپت نهایی',
  'Schedule Post': 'زمان‌بندی پست',
  'Image will be attached to this post': 'تصویر به این پست پیوست می‌شود',
  'Post to': 'انتشار در',
  '(choose one)': '(یکی را انتخاب کنید)',
  'Impact': 'تأثیر',
  'Virality': 'پتانسیل انتشار',
  'Saving…': 'در حال ذخیره…',
  'Scheduling…': 'در حال زمان‌بندی…',
  'Discarding…': 'در حال حذف…',
  'Posting to': 'در حال انتشار در',
  'Posted to': 'منتشر شد در',
  'Approve Image': 'تأیید تصویر',
  'Uploading to Drive…': 'در حال بارگذاری در Drive…',
  'Updating Google Sheets...': 'در حال به‌روزرسانی Google Sheets…',
  'Google Sheets updated.': 'Google Sheets به‌روزرسانی شد.',
  'Saving the image to Google Drive...': 'در حال ذخیره تصویر در Google Drive…',
  'Uploading image to Google Drive...': 'در حال بارگذاری تصویر در Google Drive…',
  'Saving this card for later...': 'در حال ذخیره این کارت برای بعد…',
  'Saved for later.': 'برای بعد ذخیره شد.',
  'New copy generated. Pick a variant, then approve, image, or schedule.': 'متن جدید تولید شد. یک نسخه را انتخاب کنید، سپس تأیید، تصویر یا زمان‌بندی را انجام دهید.',
  'Filtering Report': 'گزارش فیلتر',
  'Score Detail': 'جزئیات امتیاز',
  'Brand Fit': 'تناسب با برند',
  'Keywords': 'کلیدواژه‌ها',
  'Duplicate Of': 'نسخه تکراری از',
  'Routing': 'مسیردهی',
  'Fetched': 'دریافت‌شده',
  'Recent': 'جدید',
  'Quality': 'کیفیت',
  'Shortlisted': 'منتخب',
  'All Articles': 'همه مقاله‌ها',
  'Rejection Breakdown': 'جزئیات موارد ردشده',
  'Title': 'عنوان',
  'Source': 'منبع',
  'Status': 'وضعیت',
  'Score': 'امتیاز',
  'Best Brand': 'بهترین برند',
  'Detail': 'جزئیات',
  'No rejected articles': 'مقاله ردشده‌ای وجود ندارد',
  'Download PNG': 'دانلود PNG',
  'Error:': 'خطا:',
  'Token Access · BNB Chain · Smart Contracts · Retail Investors': 'دسترسی به توکن · زنجیره BNB · قراردادهای هوشمند · سرمایه‌گذاران عمومی',
  'Luxury · Web3 Culture · High-End Experiences · Aspirational': 'لوکس · فرهنگ وب ۳ · تجربه‌های سطح بالا · الهام‌بخش',
  'Full Spectrum Crypto · Markets · Policy · Technology · Culture': 'پوشش کامل رمزارز · بازارها · سیاست‌گذاری · فناوری · فرهنگ',
  'Security · DeFi Protection · Exploits · Wallet Safety · Risk Awareness': 'امنیت · حفاظت دیفای · آسیب‌پذیری‌ها · امنیت کیف پول · آگاهی از ریسک',
  '≤ 280 chars · punchy hook · 2–3 hashtags': 'حداکثر ۲۸۰ نویسه · شروع جذاب · ۲ تا ۳ هشتگ',
  'Full context · 2–4 paragraphs · brand-voice': 'شرح کامل · ۲ تا ۴ بند · لحن برند',
  'Strong opening hook · 5–10 hashtags': 'شروع قدرتمند · ۵ تا ۱۰ هشتگ',
}

export const toPersianDigits = value => String(value).replace(/\d/g, digit => '۰۱۲۳۴۵۶۷۸۹'[digit])

const initialLanguage = (() => {
  try { return window.localStorage.getItem(STORAGE_KEY) === 'fa' ? 'fa' : 'en' } catch (_) { return 'en' }
})()

export const useLanguageStore = create(set => ({
  language: initialLanguage,
  setLanguage: language => {
    const next = language === 'fa' ? 'fa' : 'en'
    try { window.localStorage.setItem(STORAGE_KEY, next) } catch (_) {}
    set({ language: next })
  },
  toggleLanguage: () => set(state => {
    const next = state.language === 'fa' ? 'en' : 'fa'
    try { window.localStorage.setItem(STORAGE_KEY, next) } catch (_) {}
    return { language: next }
  }),
}))

export function t(language, text) {
  if (language !== 'fa' || !text) return text
  return Object.entries(FA).sort(([a], [b]) => b.length - a.length).reduce(
    (value, [english, persian]) => value.replaceAll(english, persian), String(text)
  )
}

const originalText = new WeakMap()

export function localizeDocument(language) {
  const root = document.body
  if (!root) return
  const walk = () => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
    const nodes = []
    while (walker.nextNode()) nodes.push(walker.currentNode)
    nodes.forEach(node => {
      if (node.parentElement?.closest('[data-no-localize="true"]')) return
      const previous = originalText.get(node)
      const original = previous && node.nodeValue === previous.rendered
        ? previous.original
        : node.nodeValue
      const trimmed = original.trim()
      if (!trimmed) return
      const translated = language === 'fa' ? t(language, trimmed) : trimmed
      const rendered = original.replace(trimmed, translated)
      originalText.set(node, { original, rendered })
      if (node.nodeValue !== rendered) node.nodeValue = rendered
    })
  }
  walk()
  const observer = new MutationObserver(walk)
  observer.observe(root, { childList:true, subtree:true, characterData:true })
  return () => observer.disconnect()
}
