import os
import logging
import base64
import json
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

STORE_URL = "https://lafeminite1.com/ar"

# Conversation states
MAIN_MENU, ASK_PROBLEM, ASK_MORE_PROBLEMS, ASK_PREGNANT, SHOW_RESULT, PRODUCT_INQUIRY = range(6)

# ── Products Database ─────────────────────────────────────────────────────────

PRODUCTS = {
    "زيت_التين_الشوكي": {
        "name": "زيت التين الشوكي النقي",
        "url": f"{STORE_URL}/منتجات-التين-الشوكي-من-لافيمينت/c1289226895",
        "problems": ["تصبغات", "بقع داكنة", "خطوط دقيقة", "هالات سوداء", "شحوب", "بشرة باهتة", "تجاعيد", "جفاف"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "ضعي 2-3 قطرات على الوجه والرقبة بعد التنظيف، يفضل بالليل. الأسبوع الأول قد تحسين خشونة خفيفة = طبيعي، استمري.",
        "note": "بديل بوتكس طبيعي، يملأ الخطوط الدقيقة ويعبي الخطوط حول العين. عضوي معصور بارد. شهادة ECOCERT + USDA.",
        "trio": "ينصح باستخدامه مع صابونة النيلة وماسك النيلة لتصبغات قوية."
    },
    "كريم_التين_الشوكي": {
        "name": "كريم التين الشوكي",
        "url": f"{STORE_URL}/منتجات-التين-الشوكي-من-لافيمينت/c1289226895",
        "problems": ["جفاف", "خطوط دقيقة", "تجاعيد", "تفاوت لون", "شحوب", "بشرة دهنية"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "ضعي كمية مناسبة وادلكي بلطف مرتين يومياً. يناسب جميع أنواع البشرة حتى الدهنية. يُستخدم تحت المكياج.",
        "note": "خالٍ من العطور والكحول. قوام خفيف غير دهني."
    },
    "ماء_الورد": {
        "name": "ماء الورد العضوي",
        "url": f"{STORE_URL}/منتجات-العناية-بالوجه-و-الرقبة/c1957720090",
        "problems": ["احمرار وتهيج", "مسام واسعة", "جفاف", "شحوب", "بشرة غير متوازنة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "تونر يومي بعد التنظيف، أو رشه خلال اليوم. يُضاف للماسكات. يُستخدم بعد التقشير لتهدئة البشرة.",
        "note": "خالٍ من الكحول والعطور الصناعية والمواد الحافظة. شهادة ECOCERT + USDA."
    },
    "سيروم_العين": {
        "name": "سيروم العين للهالات السوداء",
        "url": f"{STORE_URL}/منتجات-العناية-بالعين-من-لافيمينت/c235543399",
        "problems": ["هالات سوداء", "انتفاخ تحت العين", "خطوط العين", "جفاف منطقة العين"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "نقطة صغيرة حول كل عين بإصبع الخاتم من الداخل للخارج. انتظري 2-3 دقائق قبل أي منتج آخر.",
        "note": "كافيين + زيت التين الشوكي + فيتامين C + هيالورونيك + ببتيدات. خالٍ من العطور والكحول."
    },
    "سيروم_الرموش": {
        "name": "سيروم الرموش والحواجب",
        "url": f"{STORE_URL}/منتجات-العناية-بالعين-من-لافيمينت/c235543399",
        "problems": ["رموش خفيفة وقصيرة", "رموش متساقطة", "حواجب فاتحة ومتفرقة", "بطء نمو الرموش والحواجب"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "للرموش: على خط الرموش مساءً قبل النوم. للحواجب: صباحاً ومساءً باتجاه نمو الشعر. النتائج الأولى بعد 15 يوم.",
        "note": "مستخلص بذور التين الشوكي 25% + بيوتين 2% + كيراتين. خالٍ من البارابين والكحول."
    },
    "صابونة_النيلة": {
        "name": "صابونة النيلة الزرقاء",
        "url": f"{STORE_URL}/منتجات-النيلة-من-لافيمينت/c418743493",
        "problems": ["تصبغات", "بقع داكنة", "مسام واسعة", "تفاوت لون", "حبوب وبثور", "آثار حبوب", "حبوب المراهقة"],
        "pregnant_safe": True,
        "sensitive_safe": False,
        "usage": "مرتين يومياً صباحاً ومساءً (بديل الغسول). اتركي الرغوة دقيقة إلى خمس دقائق. ليلاً بعدها زيت أو كريم التين الشوكي. صباحاً بعدها واقي شمس.",
        "note": "الأسبوع الأول: خشونة خفيفة = طبيعي = تقشير من الداخل، استمري. قد تسبب purging في البداية وهذا طبيعي. تناسب الجسم والبشرة. لا تناسب الأطفال.",
        "trio": "تعمل مع زيت التين الشوكي وماسك النيلة لتصبغات قوية."
    },
    "مقشر_النيلة": {
        "name": "مقشر النيلة الزرقاء",
        "url": f"{STORE_URL}/منتجات-النيلة-من-لافيمينت/c418743493",
        "problems": ["تصبغات", "بقع داكنة", "خلايا ميتة", "داكنة الركب والأكواع", "بشرة باهتة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "بللي البشرة بالماء الدافئ، دلكي بحركات دائرية، اشطفي بالماء الفاتر. 2-3 مرات أسبوعياً.",
        "note": "نتائج فورية من أول استخدام. مناسب للوجه والجسم والمناطق الحساسة. اللون الباقي على الجلد طبيعي يزول بالغسيل."
    },
    "ماسك_النيلة": {
        "name": "ماسك النيلة لتفتيح البشرة",
        "url": f"{STORE_URL}/منتجات-النيلة-من-لافيمينت/c418743493",
        "problems": ["تصبغات", "كلف", "بقع الشمس", "آثار حبوب", "مسام واسعة", "بشرة باهتة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "اغسلي وجهك، ضعي منشفة دافئة دقيقتين لفتح المسام، وزعي الماسك على الوجه والرقبة مع تجنب العين والشفاه، اتركي 15-20 دقيقة، اغسلي بماء بارد، رطبي بعدها.",
        "note": "اللذعات البسيطة أثناء الاستخدام طبيعية = الماسك يتفاعل بشكل صحيح. يفتح من أول استخدام بشكل قوي جداً لاحتوائه على الطين الأبيض المقشر الطبيعي.",
        "trio": "يعمل مع زيت التين الشوكي وصابونة النيلة للثلاثي الذهبي لتصبغات قوية."
    },
    "غسول_النيلة": {
        "name": "غسول النيلة الزرقاء للجسم",
        "url": f"{STORE_URL}/منتجات-النيلة-من-لافيمينت/c418743493",
        "problems": ["تفاوت لون الجسم", "داكنة الركب والأكواع", "جفاف الجسم", "بشرة باهتة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "بللي جسمك بالماء الدافئ، وزعي بحركات دائرية، اتركي دقيقة كاملة، اشطفي بالماء الفاتر. يومياً.",
        "note": "نيلة مغربية + زيت الأرجان + كولاجين. يناسب جميع أنواع البشرة حتى الحساسة."
    },
    "بودرة_النيلة": {
        "name": "بودرة النيلة الزرقاء",
        "url": f"{STORE_URL}/منتجات-النيلة-من-لافيمينت/c418743493",
        "problems": ["تصبغات", "بقع داكنة", "شحوب", "تفاوت لون"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "امزجي كمية مناسبة مع ماء الورد أو الحليب حتى تحصلي على قوام كريمي، ضعي على الوجه أو الجسم، اتركي 20 دقيقة، اغسلي بالماء الفاتر، رطبي بعدها. مرتين أسبوعياً.",
        "note": "مناسب للوجه والجسم وحتى البشرة الحساسة."
    },
    "مقشر_عكر_فاسي": {
        "name": "مقشر العكر الفاسي",
        "url": f"{STORE_URL}/منتجات-العكر-الفاسي-من-لافيمينت/c424452352",
        "problems": ["خلايا ميتة", "خشونة البشرة", "جلد الدجاجة", "بشرة باهتة", "تفاوت لون"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "بللي البشرة، دلكي بلطف وركزي على الأماكن الخشنة، اغسلي بالماء الفاتر، رطبي بزبدة العكر الفاسي بعدها. 2-3 مرات أسبوعياً.",
        "note": "نتائج فورية من أول استخدام. مناسب لجميع أنواع البشرة حتى الحساسة."
    },
    "زبدة_عكر_فاسي": {
        "name": "زبدة الجسم بالعكر الفاسي",
        "url": f"{STORE_URL}/منتجات-العكر-الفاسي-من-لافيمينت/c424452352",
        "problems": ["جفاف الجسم", "علامات تمدد", "خطوط بيضاء", "إكزيما", "تفاوت لون الجسم"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "بعد الاستحمام مباشرة أو قبل النوم، ضعي كمية مناسبة ودلكي بلطف حتى تمتص. يومياً.",
        "note": "ترطيب يدوم 72 ساعة. إذا وصلتكِ سائلة ضعيها في الثلاجة وستعود لقوامها."
    },
    "زيت_الارغان": {
        "name": "زيت الأرغان للجسم",
        "url": f"{STORE_URL}/منتجات-العكر-الفاسي-من-لافيمينت/c424452352",
        "problems": ["جفاف الجسم الشديد", "علامات تمدد", "خشونة اليدين والقدمين", "بشرة باهتة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "بعد الاستحمام مباشرة أو قبل النوم. يُستخدم علاجاً مكثفاً لليدين والقدمين.",
        "note": "ترطيب يدوم 72 ساعة. زيت الأرغان + زيت الورد + زيت بذور العنب."
    },
    "مجموعة_وايت_بيل": {
        "name": "مجموعة وايت بيل",
        "url": f"{STORE_URL}/وايت-بيل/c1616823754",
        "problems": ["تصبغات قوية", "اسمرار الجسم", "داكنة الركب والأكواع", "آثار الشمس", "تفاوت لون الجسم"],
        "pregnant_safe": False,
        "sensitive_safe": False,
        "usage": "الروتين الكامل: غسول ← مقشر ← كريم (يومياً) + ماسك (أسبوعياً). واقي شمس للجسم نهاراً ضروري.",
        "note": "قنبلة التفتيح — كوجيك أسيد + ألفا أربوتين + عرق سوس + لبان ذكر + كركم + زعفران. لا تناسب الحوامل والمرضعات."
    },
    "كريم_مناطق_داكنة": {
        "name": "كريم تفتيح المناطق الداكنة (الركب والأكواع)",
        "url": f"{STORE_URL}/تفتيح-المناطق-الحساسة-و-الداكنة/c2069951841",
        "problems": ["داكنة الركب والأكواع", "خشونة المفاصل", "تصبغات الاحتكاك"],
        "pregnant_safe": False,
        "sensitive_safe": True,
        "usage": "نظفي المنطقة وجففيها، ضعي كمية مناسبة، مرتين يومياً صباحاً ومساءً. ادمجيه مع مقشر العكر الفاسي لنتائج مضاعفة.",
        "note": "نعومة من أول استخدام، تفتيح واضح خلال 14 يوم. عرق السوس + يوريا + حمض الساليسيليك."
    },
    "كريم_مناطق_حساسة": {
        "name": "كريم تفتيح المناطق الحساسة",
        "url": f"{STORE_URL}/تفتيح-المناطق-الحساسة-و-الداكنة/c2069951841",
        "problems": ["اسمرار المناطق الحساسة", "حبوب المناطق الحساسة", "خشونة المناطق الحساسة"],
        "pregnant_safe": False,
        "sensitive_safe": True,
        "usage": "اغسلي المنطقة بصابونة العرق سوس، جففي بلطف، ضعي كمية مناسبة واتركي دون غسل. مرتين يومياً.",
        "note": "نتائج أقل من شهر. لا تناسب الحوامل نهائياً."
    },
    "صابونة_مناطق_حساسة": {
        "name": "صابونة تفتيح المناطق الحساسة",
        "url": f"{STORE_URL}/تفتيح-المناطق-الحساسة-و-الداكنة/c2069951841",
        "problems": ["اسمرار المناطق الحساسة", "بقع داكنة في المناطق الحساسة"],
        "pregnant_safe": False,
        "sensitive_safe": True,
        "usage": "بللي يديكِ، كوّني رغوة مناسبة، وزعي على المنطقة الحساسة بلطف، دلكي برفق ثم اشطفي. مرة واحدة مساءً فقط.",
        "note": "نتائج أقل من شهر. لا تناسب الحوامل والمرضعات."
    },
    "تبريمة_العروس": {
        "name": "تبريمة العروس المغربية",
        "url": f"{STORE_URL}/الحمام-المغربي-من-لافيمينت/c127498338",
        "problems": ["تصبغات", "اسمرار البشرة", "كلف", "خلايا ميتة", "جفاف", "بشرة باهتة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "الطريقة 1 (الحمام المغربي): حمام دافئ بخار + صابون مغربي + تبريمة 20 دقيقة + اشطفي + طبطبي فقط + زيت الأرغان. الطريقة 2: زبادي + بيضة + ليمون + 3-4 ملاعق تبريمة، 30 دقيقة، كرري 3 أيام واليوم الرابع حمام مغربي.",
        "note": "عرق سوس + نيلة + ودع + عكر فاسي + شيح + سدر + كركم."
    },
    "بدلة_الساونا": {
        "name": "بدلة الساونا الحرارية",
        "url": f"{STORE_URL}/بدله-الساونا/c1234567890",
        "problems": ["ترهل الجسم", "سيلوليت", "تسريع نتائج خلطات الجسم"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "أولاً: وزعي زيت لافمنيت أو الزبدة على جسمكِ. ثانياً: البسي البدلة (القطعة العلوية والسفلية) لتغلغل الترطيب وفتح المسامات. ثالثاً: تحركي 20 دقيقة أو ساعة (مشي خفيف أو نشاط رياضي) والبدلة تحبس الحرارة وترفع التعرق. يفضل خلال الاستخدام مقشر وليفة بحركات دائرية. لا تستخدمي أثناء الشاور أي ماسك مقشر وغسول. أخيراً: رطبي بشرتك بعد التقشير. اشربي ماء كافي قبل وبعد كل جلسة. داومي أسبوعياً لأفضل نتيجة.",
        "note": "تخصر الجسم دون التأثير على الأرداف. خامة 100% بولي يوريثان."
    },
    "حجر_خفاف": {
        "name": "حجر الخفاف",
        "url": f"{STORE_URL}/منتجات-العناية-بالوجه-و-الرقبة/c1957720090",
        "problems": ["خشونة القدمين والكعبين", "تشققات القدمين", "جلد ميت متراكم", "خشونة الركب والمرافق"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "انقعي القدمين في ماء دافئ 5-10 دقائق، بللي الحجر، افركي بحركات دائرية، ركزي على الكعبين، اشطفي وجففي، ضعي مرطب بعدها.",
        "note": "صناعة يدوية مغربية. بدّليه كل 3-6 أشهر."
    },
    "صقلة_مغربية": {
        "name": "الصقلة المغربية",
        "url": f"{STORE_URL}/الحمام-المغربي-من-لافيمينت/c127498338",
        "problems": ["خشونة الجلد", "خلايا ميتة", "تصبغات", "آثار حبوب", "بشرة باهتة"],
        "pregnant_safe": False,
        "sensitive_safe": True,
        "usage": "نظفي البشرة بالماء الفاتر، عرضي لبخار خفيف لفتح المسام، اخلطي كمية مع القليل من الماء، وزعي طبقة رقيقة، اتركي 15-20 دقيقة، افركي بلطف بحركات دائرية، اشطفي جيداً. مرة إلى مرتين أسبوعياً.",
        "note": "نعومة ونظافة من أول استخدام. لا تناسب الحوامل (كوجيك أسيد)."
    },
    "صابون_مغربي": {
        "name": "الصابون المغربي",
        "url": f"{STORE_URL}/الحمام-المغربي-من-لافيمينت/c127498338",
        "problems": ["جفاف الجسم", "بشرة باهتة", "تفاوت لون"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "رطبي البشرة بالماء الدافئ، ضعي كمية مناسبة ودلكي بلطف، اتركي بضع دقائق، افركي بالليفة المغربية الأصلية، اشطفي وجففي بلطف.",
        "note": "أوكالبتوس. أساس الحمام المغربي."
    },
    "ليفة_مغربية": {
        "name": "الليفة المغربية",
        "url": f"{STORE_URL}/الحمام-المغربي-من-لافيمينت/c127498338",
        "problems": ["خلايا ميتة", "خشونة الجسم", "سيلوليت"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "اجلسي في حمام دافئ 5-10 دقائق، ضعي الصابون المغربي واتركيه بضع دقائق، بللي الليفة وافركي بحركات دائرية لطيفة، اشطفي، رطبي بعدها. مرة إلى مرتين أسبوعياً.",
        "note": "بدّليها كل 3-6 أشهر. جففيها جيداً بعد كل استخدام."
    },
    "مورد_خدود": {
        "name": "مورد الخدود والشفاه بالعكر الفاسي",
        "url": f"{STORE_URL}/منتجات-العناية-بالشفاه-من-لافيمينت/c416482159",
        "problems": ["شحوب الخدود", "شحوب الشفاه"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "رجي العبوة جيداً، ضعي بضع نقاط على تفاحة الخدين ومنتصف الشفاه، دمجي بأطراف الأصابع بطبطبة سريعة قبل أن يجف. ضعي مرطبك قبله بـ5 دقائق للحصول على أفضل توزيع.",
        "note": "خالٍ من أصباغ صناعية وسيليكون وبارابين وكحول. آمن للبشرة الدهنية."
    },
    "مرطب_شفاه": {
        "name": "مرطب الشفاه بالعكر الفاسي",
        "url": f"{STORE_URL}/منتجات-العناية-بالشفاه-من-لافيمينت/c416482159",
        "problems": ["شفاه جافة ومتشققة", "شحوب الشفاه"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "خذي كمية صغيرة بطرف إصبعك، ضعي بلطف ووزعي بالتساوي. يومياً.",
        "note": "عكر فاسي + زبدة الشيا + زيت اللوز الحلو + فيتامين E. لون وردي طبيعي."
    },
    "مقشر_شفاه_عكر": {
        "name": "مقشر الشفاه بالعكر الفاسي",
        "url": f"{STORE_URL}/منتجات-العناية-بالشفاه-من-لافيمينت/c416482159",
        "problems": ["شفاه داكنة", "خشونة الشفاه", "شفاه جافة ومتشققة", "سواد حول الفم"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "ضعي كمية مناسبة على الشفاه، دلكي بلطف بحركات دائرية، اتركي بضع دقائق، اشطفي بلطف، ضعي مرطب الشفاه بعدها. 2-3 مرات أسبوعياً.",
        "note": "يترك توريداً طبيعياً رقيقاً يدوم بعد الاستخدام. استخدميه قبل أحمر الشفاه لمظهر مخملي."
    },
    "مقشر_شفاه_حمضيات": {
        "name": "مقشر الشفاه بالحمضيات",
        "url": f"{STORE_URL}/منتجات-العناية-بالشفاه-من-لافيمينت/c416482159",
        "problems": ["شفاه جافة ومتشققة", "شفاه داكنة", "خشونة الشفاه"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "ضعي كمية مناسبة على الشفاه النظيفة، اتركي 5-10 دقائق، اشطفي بلطف، ضعي مرطب الشفاه بالعكر الفاسي بعدها. 2-3 مرات أسبوعياً.",
        "note": "فيتامين C + عسل المانوكا النيوزلندي + زبدة الشيا + زيت الأرجان. آمن للحوامل والمرضعات."
    },
    "حجر_عكر_فاسي": {
        "name": "حجر العكر الفاسي",
        "url": f"{STORE_URL}/منتجات-العكر-الفاسي-من-لافيمينت/c424452352",
        "problems": ["شحوب الخدود", "خلطات العناية بالبشرة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "خذي كمية بسيطة، اخلطي مع ماء الورد أو ماء عادي، ضعي على المنطقة المرغوبة، اتركي فترة قصيرة ثم اشطفي.",
        "note": "تأثير مؤقت يزول مع الغسل. ليس للاستخدام اليومي المفرط."
    },
    "جواشا": {
        "name": "حجر الجواشا",
        "url": f"{STORE_URL}/منتجات-العناية-بالوجه-و-الرقبة/c1957720090",
        "problems": ["تجاعيد", "خطوط دقيقة", "بشرة متعبة"],
        "pregnant_safe": True,
        "sensitive_safe": True,
        "usage": "نظفي البشرة بصابونة النيلة، ضعي زيت التين الشوكي أو سيروم العين، حركي الحجر من الأسفل للأعلى بضغطات صغيرة 10 دقائق. عدة مرات أسبوعياً.",
        "note": "احفظيه في الثلاجة لتعزيز فعاليته."
    }
}

# ── Problem to Products Mapping ───────────────────────────────────────────────

PROBLEM_PRODUCTS = {
    # وجه
    "بشرة جافة": ["كريم_التين_الشوكي", "زيت_التين_الشوكي", "ماء_الورد", "زبدة_عكر_فاسي"],
    "بشرة دهنية": ["صابونة_النيلة", "ماء_الورد", "كريم_التين_الشوكي"],
    "بشرة مختلطة": ["ماء_الورد", "صابونة_النيلة", "كريم_التين_الشوكي"],
    "بشرة حساسة": ["ماء_الورد", "مقشر_عكر_فاسي", "كريم_التين_الشوكي"],
    "حبوب وبثور": ["صابونة_النيلة", "ماء_الورد"],
    "آثار حبوب": ["ماسك_النيلة", "زيت_التين_الشوكي", "صقلة_مغربية"],
    "مسام واسعة": ["ماسك_النيلة", "صابونة_النيلة", "ماء_الورد"],
    "بقع داكنة وتصبغات": ["زيت_التين_الشوكي", "صابونة_النيلة", "ماسك_النيلة"],
    "شحوب وإرهاق البشرة": ["زيت_التين_الشوكي", "ماسك_النيلة", "ماء_الورد"],
    "احمرار وتهيج": ["ماء_الورد", "كريم_التين_الشوكي"],
    "خطوط دقيقة": ["زيت_التين_الشوكي", "جواشا", "سيروم_العين"],
    "تجاعيد": ["زيت_التين_الشوكي", "جواشا", "كريم_التين_الشوكي"],
    "خشونة البشرة": ["مقشر_عكر_فاسي", "صقلة_مغربية"],
    "بشرة باهتة بلا إشراق": ["زيت_التين_الشوكي", "ماسك_النيلة", "صابونة_النيلة"],
    # عيون
    "هالات سوداء": ["سيروم_العين", "زيت_التين_الشوكي"],
    "انتفاخ تحت العين": ["سيروم_العين"],
    "خطوط العين": ["سيروم_العين", "زيت_التين_الشوكي", "جواشا"],
    "جفاف منطقة العين": ["سيروم_العين"],
    # جسم
    "جفاف الجسم الشديد": ["زبدة_عكر_فاسي", "زيت_الارغان", "غسول_النيلة"],
    "جلد الدجاجة": ["مقشر_عكر_فاسي", "زيت_الارغان"],
    "خشونة الجلد وتقشره": ["مقشر_عكر_فاسي", "صقلة_مغربية", "حجر_خفاف"],
    "سيلوليت": ["بدلة_الساونا", "ليفة_مغربية"],
    "علامات تمدد": ["زيت_الارغان", "زبدة_عكر_فاسي"],
    "حبوب الظهر": ["صابونة_النيلة", "صابون_مغربي"],
    "داكنة الركب والأكواع": ["كريم_مناطق_داكنة", "مقشر_عكر_فاسي", "مجموعة_وايت_بيل"],
    "داكنة الإبطين": ["كريم_مناطق_حساسة", "صابونة_مناطق_حساسة"],
    "داكنة الفخذين": ["كريم_مناطق_حساسة", "صابونة_مناطق_حساسة"],
    # مناطق حساسة
    "اسمرار المناطق الحساسة": ["كريم_مناطق_حساسة", "صابونة_مناطق_حساسة"],
    "حبوب المناطق الحساسة": ["صابونة_مناطق_حساسة", "كريم_مناطق_حساسة"],
    "خشونة المناطق الحساسة": ["كريم_مناطق_حساسة", "صابونة_مناطق_حساسة"],
    "تهيج المناطق الحساسة": ["كريم_مناطق_حساسة"],
    # شفاه
    "شفاه جافة ومتشققة": ["مرطب_شفاه", "مقشر_شفاه_حمضيات", "مقشر_شفاه_عكر"],
    "شفاه داكنة": ["مقشر_شفاه_عكر", "مقشر_شفاه_حمضيات", "مرطب_شفاه"],
    "خشونة الشفاه": ["مقشر_شفاه_عكر", "مقشر_شفاه_حمضيات"],
    "شحوب الشفاه": ["مورد_خدود", "مرطب_شفاه"],
    # رموش وحواجب
    "رموش خفيفة وقصيرة": ["سيروم_الرموش"],
    "رموش متساقطة": ["سيروم_الرموش"],
    "حواجب فاتحة ومتفرقة": ["سيروم_الرموش"],
    "بطء نمو الرموش والحواجب": ["سيروم_الرموش"],
}

ALL_PROBLEMS = list(PROBLEM_PRODUCTS.keys())

# ── Keyboards ─────────────────────────────────────────────────────────────────

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🌿 تحليل بشرتي مع أخصائية لافمنيت")],
            [KeyboardButton("💬 استفسار عن منتج")]
        ],
        resize_keyboard=True
    )

def problems_keyboard(page=0, selected=[]):
    problems_per_page = 8
    start = page * problems_per_page
    end = start + problems_per_page
    page_problems = ALL_PROBLEMS[start:end]
    buttons = []
    for i in range(0, len(page_problems), 2):
        row = []
        p1 = page_problems[i]
        check1 = "✅ " if p1 in selected else ""
        row.append(InlineKeyboardButton(f"{check1}{p1}", callback_data=f"prob_{p1}"))
        if i + 1 < len(page_problems):
            p2 = page_problems[i + 1]
            check2 = "✅ " if p2 in selected else ""
            row.append(InlineKeyboardButton(f"{check2}{p2}", callback_data=f"prob_{p2}"))
        buttons.append(row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{page-1}"))
    if end < len(ALL_PROBLEMS):
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{page+1}"))
    if nav:
        buttons.append(nav)
    if selected:
        buttons.append([InlineKeyboardButton("✅ تم الاختيار — أكملي", callback_data="done_problems")])
    return InlineKeyboardMarkup(buttons)

def pregnant_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤰 نعم، حامل أو مرضع", callback_data="pregnant_yes")],
        [InlineKeyboardButton("❌ لا", callback_data="pregnant_no")]
    ])

# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🌿 *أهلاً بكِ في بوت لافمنيت للعناية الطبيعية*\n\n"
        "أنا أخصائية البشرة من لافمنيت 💚\n"
        "كيف أقدر أساعدك اليوم؟",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "تحليل" in text:
        context.user_data["selected_problems"] = []
        context.user_data["page"] = 0
        await update.message.reply_text(
            "💆‍♀️ *تحليل البشرة مع أخصائية لافمنيت*\n\n"
            "اختاري مشكلتك أو مشاكلك من القائمة 👇\n"
            "_(يمكنك اختيار أكثر من مشكلة)_",
            parse_mode="Markdown",
            reply_markup=problems_keyboard(0, [])
        )
        return ASK_PROBLEM
    elif "استفسار" in text:
        await update.message.reply_text(
            "💬 *استفساراتك عن منتجات لافمنيت*\n\n"
            "اكتبي سؤالك وسأجيبك مباشرة 🌿\n\n"
            "مثال: كيف أستخدم صابونة النيلة؟ هل زيت التين مناسب للحامل؟",
            parse_mode="Markdown"
        )
        return PRODUCT_INQUIRY
    return MAIN_MENU

async def handle_problem_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    selected = context.user_data.get("selected_problems", [])
    page = context.user_data.get("page", 0)

    if data.startswith("prob_"):
        prob = data[5:]
        if prob in selected:
            selected.remove(prob)
        else:
            selected.append(prob)
        context.user_data["selected_problems"] = selected
        await query.edit_message_reply_markup(reply_markup=problems_keyboard(page, selected))

    elif data.startswith("page_"):
        page = int(data[5:])
        context.user_data["page"] = page
        await query.edit_message_reply_markup(reply_markup=problems_keyboard(page, selected))

    elif data == "done_problems":
        if not selected:
            await query.answer("اختاري مشكلة واحدة على الأقل!", show_alert=True)
            return ASK_PROBLEM
        await query.edit_message_text(
            f"✅ اخترتِ: {', '.join(selected)}\n\n"
            "سؤال أخير 🤰",
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "هل أنتِ حامل أو مرضع؟",
            reply_markup=pregnant_keyboard()
        )
        return ASK_PREGNANT

    return ASK_PROBLEM

async def handle_pregnant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pregnant = query.data == "pregnant_yes"
    context.user_data["pregnant"] = pregnant
    await query.edit_message_text(
        "⏳ جاري تحضير توصياتك الشخصية..."
    )
    report = build_recommendations(context)
    restart_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تحليل جديد", callback_data="restart")],
        [InlineKeyboardButton("💬 استفسار عن منتج", callback_data="inquiry")]
    ])
    await query.message.reply_text(report, parse_mode="Markdown", reply_markup=restart_kb)
    return SHOW_RESULT

def build_recommendations(context):
    selected = context.user_data.get("selected_problems", [])
    pregnant = context.user_data.get("pregnant", False)
    recommended = {}
    for prob in selected:
        prod_keys = PROBLEM_PRODUCTS.get(prob, [])
        for key in prod_keys:
            if key not in recommended:
                recommended[key] = []
            recommended[key].append(prob)

    # Filter for pregnant
    if pregnant:
        safe_recommended = {k: v for k, v in recommended.items() if PRODUCTS[k]["pregnant_safe"]}
    else:
        safe_recommended = recommended

    if not safe_recommended:
        return "⚠️ لم نجد منتجات مناسبة لمشاكلك مع مراعاة حالتك. تواصلي معنا مباشرة عبر المتجر للمساعدة."

    # Sort by number of problems solved
    sorted_products = sorted(safe_recommended.items(), key=lambda x: len(x[1]), reverse=True)
    top_products = sorted_products[:4]

    report = "✨ *توصيات أخصائية لافمنيت لكِ*\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    report += f"🎯 *مشاكلك:* {', '.join(selected)}\n\n"

    if pregnant:
        report += "🤰 *تم مراعاة الحمل/الرضاعة في التوصيات*\n\n"

    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += "🛒 *المنتجات المناسبة لكِ:*\n\n"

    for key, probs in top_products:
        prod = PRODUCTS[key]
        report += f"🌿 *{prod['name']}*\n"
        report += f"✅ يعالج: {', '.join(probs)}\n"
        report += f"📋 {prod['usage']}\n"
        if prod.get("note"):
            report += f"💡 {prod['note']}\n"
        report += f"🔗 {prod['url']}\n\n"

    # Check trio recommendation
    trio_probs = ["تصبغات", "بقع داكنة وتصبغات", "شحوب وإرهاق البشرة"]
    if any(p in selected for p in trio_probs) and not pregnant:
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += "⭐ *التوصية الذهبية لتصبغاتك:*\n"
        report += "الثلاثي السحري: زيت التين الشوكي + صابونة النيلة + ماسك النيلة\n"
        report += "نتائج ملحوظة من 10-14 يوم 💚\n\n"

    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += f"🛍️ *تسوقي الآن:* {STORE_URL}\n"
    report += "📞 *للاستفسار:* تواصلي معنا عبر المتجر مباشرة"
    return report

async def handle_product_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    typing_msg = await update.message.reply_text("⏳ جاري البحث عن إجابتك...")

    # Build products knowledge base for Claude
    products_info = ""
    for key, prod in PRODUCTS.items():
        products_info += f"\n\nمنتج: {prod['name']}\n"
        products_info += f"الاستخدام: {prod['usage']}\n"
        products_info += f"ملاحظات: {prod.get('note', '')}\n"
        products_info += f"آمن للحامل/المرضع: {'نعم' if prod['pregnant_safe'] else 'لا'}\n"
        products_info += f"يعالج: {', '.join(prod['problems'])}\n"

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [{
            "role": "user",
            "content": f"""أنتِ أخصائية بشرة من براند لافمنيت للعناية الطبيعية. 
أجيبي على سؤال العميلة بشكل ودود ومختصر وواضح.
لا تذكري أبداً كلمة "ذكاء اصطناعي" أو "بوت" - أنتِ أخصائية بشرة حقيقية من لافمنيت.
استخدمي المعلومات التالية عن منتجات لافمنيت للإجابة:

{products_info}

سؤال العميلة: {question}

أجيبي بالعربية بشكل ودود ومختصر. إذا السؤال خارج نطاق منتجات لافمنيت، وجهيها للتواصل مع المتجر مباشرة."""
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=payload
            )
            resp.raise_for_status()
            answer = resp.json()["content"][0]["text"]
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        answer = "عذراً، حدث خطأ. تواصلي معنا مباشرة عبر المتجر وسنساعدك 💚"

    await typing_msg.delete()
    restart_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 سؤال آخر", callback_data="inquiry")],
        [InlineKeyboardButton("🌿 تحليل بشرتي", callback_data="restart")]
    ])
    await update.message.reply_text(
        answer + f"\n\n🛍️ للطلب: {STORE_URL}",
        reply_markup=restart_kb
    )
    return PRODUCT_INQUIRY

async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "restart":
        context.user_data.clear()
        context.user_data["selected_problems"] = []
        context.user_data["page"] = 0
        await query.message.reply_text(
            "💆‍♀️ *تحليل جديد — اختاري مشكلتك أو مشاكلك:*",
            parse_mode="Markdown",
            reply_markup=problems_keyboard(0, [])
        )
        return ASK_PROBLEM
    elif query.data == "inquiry":
        await query.message.reply_text(
            "💬 اكتبي سؤالك عن أي منتج من لافمنيت 🌿"
        )
        return PRODUCT_INQUIRY

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسلي /start للبدء من جديد 🌿")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            ASK_PROBLEM: [CallbackQueryHandler(handle_problem_selection)],
            ASK_PREGNANT: [CallbackQueryHandler(handle_pregnant, pattern="^pregnant_")],
            SHOW_RESULT: [CallbackQueryHandler(handle_restart, pattern="^(restart|inquiry)$")],
            PRODUCT_INQUIRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_inquiry),
                CallbackQueryHandler(handle_restart, pattern="^(restart|inquiry)$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    logger.info("🌿 لافمنيت بوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
