# Default settings
DEFAULT_NEED_LANG = [
    "Chinese",
    "Spanish",
    "Japanese",
    "Korean",
    "Thai",
    "Arabic",
    "German",
    "French",
    "Italian",
    "Russian",
    "Portuguese",
    "Indonesian",
    "Hindi",
    "Telugu",
    "Tamil",
    "Urdu",
    "Vietnamese",
    "Malay",
    "Norwegian",
    "Swedish",
    "Finnish",
    "Danish",
    "Dutch",
    "Catalan",
    "Hebrew",
    "Greek",
    "Hungarian",
    "Polish",
    "Czech",
    "Slovak",
    "Romanian",
    "Slovenian",
    "Croatian",
    "Bulgarian",
    "Turkish",
    "Ukrainian",
    "Icelandic",
    "Filipino",
    "Swahili",
    "Mongolian",
    "Persian",
    "Kazakh",
    "Uzbek",
]
DEFAULT_STYLE = [
    "sad",
    "chat",
    "calm",
    "angry",
    "sorry",
    "gentle",
    "serious",
    "fearful",
    "excited",
    "envious",
    "lyrical",
    "hopeful",
    "cheerful",
    "newscast",
    "friendly",
    "shouting",
    "depressed",
    "terrified",
    "assistant",
    "unfriendly",
    "whispering",
    "empathetic",
    "disgruntled",
    "embarrassed",
    "chat-casual",
    "conversation",
    "affectionate",
    "poetry-reading",
    "livecommercial",
    "newscast-formal",
    "customerservice",
    "newscast-casual",
    "sports-commentary",
    "narration-relaxed",
    "advertisement-upbeat",
    "documentary-narration",
    "narration-professional",
    "sports-commentary-excited",
]
DEFAULT_SCENE = [
    "chat-casual",
    "conversation",
    "livecommercial",
    "sorry",
    "speech",
    "broadcast",
    "interviews",
]
DEFAULT_PROMPT_PREFIX = (
    "Translate the following English sentence into the Chinese. Return the translation alongside the original English sentence. "
    "Ensure the translation retains the original meaning and follows the word order of the English sentence, while maintaining "
    "grammatical correctness and fluency. Provide the translations in the following format, including the original English sentence "
    "without any additional content:"
)
DEFAULT_STYLE_SUFFIX = "Style: [Choose one from: " + ", ".join(DEFAULT_STYLE) + "]"
DEFAULT_SCENE_SUFFIX = "Scene: [Choose one from: " + ", ".join(DEFAULT_SCENE) + "]"
DEFAULT_MAX_TOKENS = 12000

ISO_MAP = {
    "zh-cn": {"english": "Chinese", "chinese": "中文", "nllb": "zho_Hans"},
    "en": {"english": "English", "chinese": "英语", "nllb": "eng_Latn"},
    "es": {"english": "Spanish", "chinese": "西班牙语", "nllb": "spa_Latn"},
    "ja": {"english": "Japanese", "chinese": "日语", "nllb": "jpn_Jpan"},
    "ko": {"english": "Korean", "chinese": "韩语", "nllb": "kor_Hang"},
    "th": {"english": "Thai", "chinese": "泰语", "nllb": "tha_Thai"},
    "ar": {"english": "Arabic", "chinese": "阿拉伯语", "nllb": "arb_Arab"},
    "de": {"english": "German", "chinese": "德语", "nllb": "deu_Latn"},
    "fr": {"english": "French", "chinese": "法语", "nllb": "fra_Latn"},
    "it": {"english": "Italian", "chinese": "意大利语", "nllb": "ita_Latn"},
    "ru": {"english": "Russian", "chinese": "俄语", "nllb": "rus_Cyrl"},
    "pt": {"english": "Portuguese", "chinese": "葡萄牙语", "nllb": "por_Latn"},
    "id": {"english": "Indonesian", "chinese": "印尼语", "nllb": "ind_Latn"},
    "hi": {"english": "Hindi", "chinese": "印地语", "nllb": "hin_Deva"},
    "te": {"english": "Telugu", "chinese": "泰卢固语", "nllb": "tel_Telu"},
    "ta": {"english": "Tamil", "chinese": "泰米尔语", "nllb": "tam_Taml"},
    "ur": {"english": "Urdu", "chinese": "乌尔都语", "nllb": "urd_Arab"},
    "vi": {"english": "Vietnamese", "chinese": "越南语", "nllb": "vie_Latn"},
    "ms": {"english": "Malay", "chinese": "马来语", "nllb": "zsm_Latn"},
    "no": {"english": "Norwegian", "chinese": "挪威语", "nllb": "nob_Latn"},
    "sv": {"english": "Swedish", "chinese": "瑞典语", "nllb": "swe_Latn"},
    "fi": {"english": "Finnish", "chinese": "芬兰语", "nllb": "fin_Latn"},
    "da": {"english": "Danish", "chinese": "丹麦语", "nllb": "dan_Latn"},
    "nl": {"english": "Dutch", "chinese": "荷兰语", "nllb": "nld_Latn"},
    "ca": {"english": "Catalan", "chinese": "加泰罗尼亚语", "nllb": "cat_Latn"},
    "he": {"english": "Hebrew", "chinese": "希伯来语", "nllb": "heb_Hebr"},
    "el": {"english": "Greek", "chinese": "希腊语", "nllb": "ell_Grek"},
    "hu": {"english": "Hungarian", "chinese": "匈牙利语", "nllb": "hun_Latn"},
    "pl": {"english": "Polish", "chinese": "波兰语", "nllb": "pol_Latn"},
    "cs": {"english": "Czech", "chinese": "捷克语", "nllb": "ces_Latn"},
    "sk": {"english": "Slovak", "chinese": "斯洛伐克语", "nllb": "slk_Latn"},
    "ro": {"english": "Romanian", "chinese": "罗马尼亚语", "nllb": "ron_Latn"},
    "sl": {"english": "Slovenian", "chinese": "斯洛文尼亚语", "nllb": "slv_Latn"},
    "hr": {"english": "Croatian", "chinese": "克罗地亚语", "nllb": "hrv_Latn"},
    "bg": {"english": "Bulgarian", "chinese": "保加利亚语", "nllb": "bul_Cyrl"},
    "tr": {"english": "Turkish", "chinese": "土耳其语", "nllb": "tur_Latn"},
    "uk": {"english": "Ukrainian", "chinese": "乌克兰语", "nllb": "ukr_Cyrl"},
    "is": {"english": "Icelandic", "chinese": "冰岛语", "nllb": "isl_Latn"},
    "fil": {"english": "Filipino", "chinese": "菲律宾语", "nllb": "fil_Latn"},
    "sw": {"english": "Swahili", "chinese": "斯瓦希里语", "nllb": "swh_Latn"},
    "mn": {"english": "Mongolian", "chinese": "蒙古语", "nllb": "khk_Cyrl"},
    "fa": {"english": "Persian", "chinese": "波斯语", "nllb": "pes_Arab"},
    "kk": {"english": "Kazakh", "chinese": "哈萨克语", "nllb": "kaz_Cyrl"},
    "uz": {"english": "Uzbek", "chinese": "乌兹别克语", "nllb": "uzn_Latn"},
}

