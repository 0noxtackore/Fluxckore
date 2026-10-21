"""Translation manager (104 languages) with automatic system-language detection."""
import ctypes
import json
import os
import sys

from .core.system import project_root


class TranslationManager:
    """Singleton that loads and serves translations from JSON."""

    _instance = None
    _translations = {}
    _current_lang = "en"
    _available_langs = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_translations()
        return cls._instance

    @classmethod
    def _get_translations_path(cls):
        """Path to the translations JSON file."""
        return os.path.join(project_root(), "locales", "translations.json")

    @classmethod
    def _load_translations(cls):
        """Load translations from the JSON file."""
        try:
            path = cls._get_translations_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._translations = json.load(f)
                    cls._available_langs = set(cls._translations.keys())
                print(f"[i18n] Loaded {len(cls._available_langs)} languages")
            else:
                print(f"[i18n] Warning: translations.json not found at {path}")
                cls._translations = {}
                cls._available_langs = set()
        except Exception as e:
            print(f"[i18n] Error loading translations: {e}")
            cls._translations = {}
            cls._available_langs = set()

    @classmethod
    def detect_system_language(cls):
        """Detect the system language (Windows UI language first)."""
        try:
            # 1) Windows UI language (Settings > Language).
            try:
                lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                lang_code = cls._langid_to_code(lang_id)
                if lang_code and lang_code in cls._available_langs:
                    print(f"[i18n] Detected Windows UI language: {lang_code} (LANGID: {hex(lang_id)})")
                    return lang_code
            except Exception as e:
                print(f"[i18n] Could not detect UI language: {e}")

            # 2) System locale.
            try:
                lang_id = ctypes.windll.kernel32.GetSystemDefaultLangID()
                lang_code = cls._langid_to_code(lang_id)
                if lang_code and lang_code in cls._available_langs:
                    print(f"[i18n] Detected system locale: {lang_code} (LANGID: {hex(lang_id)})")
                    return lang_code
            except Exception:
                pass

            # 3) Keyboard layout as fallback.
            try:
                hkl = ctypes.windll.user32.GetKeyboardLayout(0)
                lang_id = hkl & 0xFFFF
                if lang_id:
                    lang_code = cls._langid_to_code(lang_id)
                    if lang_code and lang_code in cls._available_langs:
                        print(f"[i18n] Detected keyboard language: {lang_code} (LANGID: {hex(lang_id)})")
                        return lang_code
            except Exception:
                pass

            # 4) Python locale as last resort.
            import locale
            lang = locale.getdefaultlocale()[0]
            if lang:
                lang_code = lang.split("_")[0].lower()
                if lang_code in cls._available_langs:
                    print(f"[i18n] Detected Python locale: {lang_code}")
                    return lang_code
                if lang.lower().replace("-", "_") in cls._available_langs:
                    return lang.lower().replace("-", "_")
        except Exception as e:
            print(f"[i18n] Error detecting language: {e}")

        return "en"

    @staticmethod
    def _langid_to_code(lang_id):
        """Convert a Windows LANGID to an ISO language code."""
        LANGID_MAP = {
            # English variants
            0x0409: "en", 0x0809: "en", 0x0C09: "en", 0x1009: "en", 0x1409: "en",
            0x1809: "en", 0x1C09: "en", 0x2009: "en", 0x2409: "en", 0x2809: "en",
            0x2C09: "en", 0x3009: "en", 0x3409: "en", 0x4409: "en", 0x4009: "en",
            0x4809: "en",
            # Spanish variants
            0x0C0A: "es", 0x040A: "es", 0x080A: "es", 0x100A: "es", 0x140A: "es",
            0x180A: "es", 0x1C0A: "es", 0x200A: "es", 0x240A: "es", 0x280A: "es",
            0x2C0A: "es", 0x300A: "es", 0x340A: "es", 0x380A: "es", 0x3C0A: "es",
            0x400A: "es", 0x440A: "es", 0x480A: "es", 0x4C0A: "es", 0x500A: "es",
            0x580A: "es",
            # French variants
            0x040C: "fr", 0x080C: "fr", 0x0C0C: "fr", 0x100C: "fr", 0x140C: "fr",
            0x180C: "fr", 0xE40C: "fr",
            # German variants
            0x0407: "de", 0x0807: "de", 0x0C07: "de", 0x1007: "de", 0x1407: "de",
            # Portuguese
            0x0416: "pt", 0x0816: "pt",
            # Italian
            0x0410: "it", 0x0810: "it",
            # Russian
            0x0419: "ru", 0x0819: "ru",
            # Japanese
            0x0411: "ja",
            # Chinese variants
            0x0804: "zh", 0x1004: "zh", 0x0404: "zh-TW", 0x0C04: "zh-TW", 0x1404: "zh-TW",
            # Korean
            0x0412: "ko", 0x0812: "ko",
            # Arabic variants
            0x0401: "ar", 0x0801: "ar", 0x0C01: "ar", 0x1001: "ar", 0x1401: "ar",
            0x1801: "ar", 0x1C01: "ar", 0x2001: "ar", 0x2401: "ar", 0x2801: "ar",
            0x2C01: "ar", 0x3001: "ar", 0x3401: "ar", 0x3801: "ar", 0x3C01: "ar",
            0x4001: "ar",
            # Hindi
            0x0439: "hi",
            # Dutch
            0x0413: "nl", 0x0813: "nl",
            # Polish
            0x0415: "pl",
            # Turkish
            0x041F: "tr",
            # Swedish
            0x041D: "sv", 0x081D: "sv",
            # Czech
            0x0405: "cs",
            # Greek
            0x0408: "el",
            # Hebrew
            0x040D: "he", 0x080D: "he",
            # Thai
            0x041E: "th",
            # Vietnamese
            0x042A: "vi",
            # Indonesian
            0x0421: "id",
            # Other common languages
            0x0425: "et", 0x0426: "lv", 0x0427: "lt", 0x0429: "fa", 0x042B: "hy",
            0x042C: "az", 0x0431: "eu", 0x0432: "tn", 0x0434: "xh", 0x0435: "zu",
            0x0436: "af", 0x0437: "ka", 0x0438: "fo", 0x043A: "mt", 0x043B: "se",
            0x043E: "ms", 0x083E: "ms", 0x043F: "kk", 0x0440: "ky", 0x0441: "sw",
            0x0442: "tk", 0x0443: "uz", 0x0843: "uz", 0x0444: "tt", 0x0445: "bn",
            0x0845: "bn", 0x0446: "pa", 0x0447: "gu", 0x0448: "or", 0x0449: "ta",
            0x044A: "te", 0x044B: "kn", 0x044C: "ml", 0x044D: "as", 0x044E: "mr",
            0x044F: "sa", 0x0450: "mn", 0x0850: "mn", 0x0451: "bo", 0x0851: "bo",
            0x0452: "cy", 0x0453: "km", 0x0454: "lo", 0x0455: "my", 0x0456: "gl",
            0x0457: "kok", 0x0458: "mni", 0x0459: "sd", 0x045A: "syr", 0x045B: "si",
            0x045C: "chr", 0x045D: "iu", 0x085D: "iu", 0x045E: "am", 0x045F: "tzm",
            0x0460: "ks", 0x0860: "ks", 0x0461: "ne", 0x0861: "ne", 0x0462: "fy",
            0x0463: "ps", 0x0464: "fil", 0x0465: "dv", 0x0466: "bin", 0x0467: "ff",
            0x0468: "ha", 0x0469: "ibb", 0x046A: "yo", 0x046B: "quz", 0x086B: "quz",
            0x0C6B: "quz", 0x046C: "nso", 0x046D: "ba", 0x046E: "lb", 0x046F: "kl",
            0x0470: "ig", 0x0471: "kr", 0x0472: "om", 0x0473: "ti", 0x0873: "ti",
            0x0474: "gn", 0x0475: "haw", 0x0476: "la", 0x0477: "so", 0x0478: "ii",
            0x0479: "pap", 0x047A: "arn", 0x047C: "moh", 0x047E: "br", 0x0480: "ug",
            0x0880: "ug", 0x0481: "mi", 0x0482: "oc", 0x0483: "co", 0x0484: "gsw",
            0x0485: "sah", 0x0486: "qut", 0x0487: "rw", 0x0488: "wo", 0x048C: "fa",
            0x048D: "gd", 0x0491: "ga", 0x0492: "sq", 0x0493: "ro", 0x0494: "hr",
            0x081A: "sr", 0x0C1A: "sr", 0x1C1A: "sr", 0x181A: "sr",
            0x041A: "hr", 0x101A: "hr", 0x041B: "sk", 0x042D: "eu", 0x042E: "hsb",
            0x082E: "dsb", 0x041C: "sq", 0x041D: "sv", 0x041F: "tr", 0x0422: "uk",
            0x0423: "be", 0x0424: "sl", 0x0428: "tg", 0x042B: "hy", 0x042C: "az",
            0x082C: "az", 0x042F: "mk", 0x0430: "st", 0x0432: "tn", 0x0434: "xh",
            0x0435: "zu", 0x0436: "af", 0x0437: "ka", 0x0438: "fo", 0x043A: "mt",
            0x047F: "ti", 0x0495: "bs", 0x201A: "bs", 0x141A: "bs",
        }
        return LANGID_MAP.get(lang_id)

    @classmethod
    def translate(cls, text, lang=None):
        """Translate a text to the given (or current) language."""
        if lang is None:
            lang = cls._current_lang

        if lang not in cls._translations:
            return text

        translations = cls._translations[lang].get("translations", {})
        return translations.get(text, text)

    @classmethod
    def get_translations(cls, lang=None):
        """Return the raw translations dict of the given (or current) language."""
        lang = lang or cls._current_lang
        return cls._translations.get(lang, {}).get("translations", {})

    @classmethod
    def set_language(cls, lang):
        """Set the current language."""
        if lang in cls._available_langs:
            cls._current_lang = lang
            return True
        return False

    @classmethod
    def get_available_languages(cls):
        """Return the set of available language codes."""
        return cls._available_langs.copy()

    @classmethod
    def get_current_language(cls):
        """Return the current language code."""
        return cls._current_lang


def _(text):
    """Translate a text to the current language."""
    return TranslationManager.translate(text)


# Language display options with emoji flags.
LANGUAGE_OPTIONS = {
    "en": {"flag": "🇺🇸", "name": "English", "native": "English"},
    "es": {"flag": "🇪🇸", "name": "Spanish", "native": "Español"},
    "fr": {"flag": "🇫🇷", "name": "French", "native": "Français"},
    "de": {"flag": "🇩🇪", "name": "German", "native": "Deutsch"},
    "pt": {"flag": "🇧🇷", "name": "Portuguese", "native": "Português"},
    "it": {"flag": "🇮🇹", "name": "Italian", "native": "Italiano"},
    "ru": {"flag": "🇷🇺", "name": "Russian", "native": "Русский"},
    "ja": {"flag": "🇯🇵", "name": "Japanese", "native": "日本語"},
    "zh": {"flag": "🇨🇳", "name": "Chinese", "native": "简体中文"},
    "zh-TW": {"flag": "🇹🇼", "name": "Chinese (Traditional)", "native": "繁體中文"},
    "ko": {"flag": "🇰🇷", "name": "Korean", "native": "한국어"},
    "ar": {"flag": "🇸🇦", "name": "Arabic", "native": "العربية"},
    "hi": {"flag": "🇮🇳", "name": "Hindi", "native": "हिन्दी"},
    "nl": {"flag": "🇳🇱", "name": "Dutch", "native": "Nederlands"},
    "pl": {"flag": "🇵🇱", "name": "Polish", "native": "Polski"},
    "tr": {"flag": "🇹🇷", "name": "Turkish", "native": "Türkçe"},
    "sv": {"flag": "🇸🇪", "name": "Swedish", "native": "Svenska"},
    "cs": {"flag": "🇨🇿", "name": "Czech", "native": "Čeština"},
    "el": {"flag": "🇬🇷", "name": "Greek", "native": "Ελληνικά"},
    "he": {"flag": "🇮🇱", "name": "Hebrew", "native": "עברית"},
    "th": {"flag": "🇹🇭", "name": "Thai", "native": "ไทย"},
    "vi": {"flag": "🇻🇳", "name": "Vietnamese", "native": "Tiếng Việt"},
    "id": {"flag": "🇮🇩", "name": "Indonesian", "native": "Bahasa Indonesia"},
    "ms": {"flag": "🇲🇾", "name": "Malay", "native": "Bahasa Melayu"},
    "ro": {"flag": "🇷🇴", "name": "Romanian", "native": "Română"},
    "hu": {"flag": "🇭🇺", "name": "Hungarian", "native": "Magyar"},
    "da": {"flag": "🇩🇰", "name": "Danish", "native": "Dansk"},
    "fi": {"flag": "🇫🇮", "name": "Finnish", "native": "Suomi"},
    "no": {"flag": "🇳🇴", "name": "Norwegian", "native": "Norsk"},
    "uk": {"flag": "🇺🇦", "name": "Ukrainian", "native": "Українська"},
    "bg": {"flag": "🇧🇬", "name": "Bulgarian", "native": "Български"},
    "hr": {"flag": "🇭🇷", "name": "Croatian", "native": "Hrvatski"},
    "sr": {"flag": "🇷🇸", "name": "Serbian", "native": "Српски"},
    "sk": {"flag": "🇸🇰", "name": "Slovak", "native": "Slovenčina"},
    "sl": {"flag": "🇸🇮", "name": "Slovenian", "native": "Slovenščina"},
    "lt": {"flag": "🇱🇹", "name": "Lithuanian", "native": "Lietuvių"},
    "lv": {"flag": "🇱🇻", "name": "Latvian", "native": "Latviešu"},
    "et": {"flag": "🇪🇪", "name": "Estonian", "native": "Eesti"},
    "ca": {"flag": "🇦🇩", "name": "Catalan", "native": "Català"},
    "af": {"flag": "🇿🇦", "name": "Afrikaans", "native": "Afrikaans"},
    "sq": {"flag": "🇦🇱", "name": "Albanian", "native": "Shqip"},
    "am": {"flag": "🇪🇹", "name": "Amharic", "native": "አማርኛ"},
    "hy": {"flag": "🇦🇲", "name": "Armenian", "native": "Հայերեն"},
    "az": {"flag": "🇦🇿", "name": "Azerbaijani", "native": "Azərbaycan"},
    "eu": {"flag": "🇪🇸", "name": "Basque", "native": "Euskara"},
    "bn": {"flag": "🇧🇩", "name": "Bengali", "native": "বাংলা"},
    "bs": {"flag": "🇧🇦", "name": "Bosnian", "native": "Bosanski"},
    "my": {"flag": "🇲🇲", "name": "Burmese", "native": "မြန်မာ"},
    "ceb": {"flag": "🇵🇭", "name": "Cebuano", "native": "Cebuano"},
    "ny": {"flag": "🇲🇼", "name": "Chichewa", "native": "Chichewa"},
    "co": {"flag": "🇫🇷", "name": "Corsican", "native": "Corsu"},
    "eo": {"flag": "🌍", "name": "Esperanto", "native": "Esperanto"},
    "tl": {"flag": "🇵🇭", "name": "Filipino", "native": "Filipino"},
    "fy": {"flag": "🇳🇱", "name": "Frisian", "native": "Frysk"},
    "gl": {"flag": "🇪🇸", "name": "Galician", "native": "Galego"},
    "ka": {"flag": "🇬🇪", "name": "Georgian", "native": "ქართული"},
    "gu": {"flag": "🇮🇳", "name": "Gujarati", "native": "ગુજરાતી"},
    "ht": {"flag": "🇭🇹", "name": "Haitian Creole", "native": "Kreyòl"},
    "ha": {"flag": "🇳🇬", "name": "Hausa", "native": "Hausa"},
    "haw": {"flag": "🇺🇸", "name": "Hawaiian", "native": "Hawaiian"},
    "iw": {"flag": "🇮🇱", "name": "Hebrew", "native": "עברית"},
    "hmn": {"flag": "🇨🇳", "name": "Hmong", "native": "Hmong"},
    "is": {"flag": "🇮🇸", "name": "Icelandic", "native": "Íslenska"},
    "ig": {"flag": "🇳🇬", "name": "Igbo", "native": "Igbo"},
    "ga": {"flag": "🇮🇪", "name": "Irish", "native": "Gaeilge"},
    "jw": {"flag": "🇮🇩", "name": "Javanese", "native": "Jawa"},
    "kn": {"flag": "🇮🇳", "name": "Kannada", "native": "ಕನ್ನಡ"},
    "kk": {"flag": "🇰🇿", "name": "Kazakh", "native": "Қазақ"},
    "km": {"flag": "🇰🇭", "name": "Khmer", "native": "ខ្មែរ"},
    "ku": {"flag": "🇮🇶", "name": "Kurdish", "native": "Kurdî"},
    "ky": {"flag": "🇰🇬", "name": "Kyrgyz", "native": "Кыргызча"},
    "lo": {"flag": "🇱🇦", "name": "Lao", "native": "ລາວ"},
    "la": {"flag": "🏛️", "name": "Latin", "native": "Latina"},
    "lb": {"flag": "🇱🇺", "name": "Luxembourgish", "native": "Lëtzebuergesch"},
    "mk": {"flag": "🇲🇰", "name": "Macedonian", "native": "Македонски"},
    "mg": {"flag": "🇲🇬", "name": "Malagasy", "native": "Malagasy"},
    "ml": {"flag": "🇮🇳", "name": "Malayalam", "native": "മലയാളം"},
    "mt": {"flag": "🇲🇹", "name": "Maltese", "native": "Malti"},
    "mi": {"flag": "🇳🇿", "name": "Maori", "native": "Māori"},
    "mr": {"flag": "🇮🇳", "name": "Marathi", "native": "मराठी"},
    "mn": {"flag": "🇲🇳", "name": "Mongolian", "native": "Монгол"},
    "ne": {"flag": "🇳🇵", "name": "Nepali", "native": "नेपाली"},
    "ps": {"flag": "🇦🇫", "name": "Pashto", "native": "پښتو"},
    "fa": {"flag": "🇮🇷", "name": "Persian", "native": "فارسی"},
    "pa": {"flag": "🇮🇳", "name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    "sm": {"flag": "🇼🇸", "name": "Samoan", "native": "Gagana Samoa"},
    "gd": {"flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "name": "Scottish Gaelic", "native": "Gàidhlig"},
    "st": {"flag": "🇱🇸", "name": "Sesotho", "native": "Sesotho"},
    "sn": {"flag": "🇿🇼", "name": "Shona", "native": "Shona"},
    "sd": {"flag": "🇵🇰", "name": "Sindhi", "native": "سنڌي"},
    "si": {"flag": "🇱🇰", "name": "Sinhala", "native": "සිංහල"},
    "so": {"flag": "🇸🇴", "name": "Somali", "native": "Soomaali"},
    "su": {"flag": "🇮🇩", "name": "Sundanese", "native": "Basa Sunda"},
    "sw": {"flag": "🇹🇿", "name": "Swahili", "native": "Kiswahili"},
    "tg": {"flag": "🇹🇯", "name": "Tajik", "native": "Тоҷикӣ"},
    "ta": {"flag": "🇮🇳", "name": "Tamil", "native": "தமிழ்"},
    "te": {"flag": "🇮🇳", "name": "Telugu", "native": "తెలుగు"},
    "ur": {"flag": "🇵🇰", "name": "Urdu", "native": "اردو"},
    "uz": {"flag": "🇺🇿", "name": "Uzbek", "native": "O'zbek"},
    "cy": {"flag": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "name": "Welsh", "native": "Cymraeg"},
    "xh": {"flag": "🇿🇦", "name": "Xhosa", "native": "isiXhosa"},
    "yi": {"flag": "🇮🇱", "name": "Yiddish", "native": "ייִדיש"},
    "yo": {"flag": "🇳🇬", "name": "Yoruba", "native": "Yorùbá"},
    "zu": {"flag": "🇿🇦", "name": "Zulu", "native": "isiZulu"},
}
