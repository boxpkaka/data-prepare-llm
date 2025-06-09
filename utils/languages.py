ISO = {
    "Chinese": "zh-cn",
    "English": "en",
    "Spanish": "es",
    "Japanese": "ja",
    "Korean": "ko",
    "Thai": "th",
    "Arabic": "ar",
    "German": "de",
    "French": "fr",
    "Italian": "it",
    "Russian": "ru",
    "Portuguese": "pt",
    "Indonesian": "id",
    "Hindi": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Malay": "ms",
    "Norwegian": "no",
    "Swedish": "sv",
    "Finnish": "fi",
    "Danish": "da",
    "Dutch": "nl",
    "Catalan": "ca",
    "Hebrew": "he",
    "Greek": "el",
    "Hungarian": "hu",
    "Polish": "pl",
    "Czech": "cs",
    "Slovak": "sk",
    "Romanian": "ro",
    "Slovenian": "sl",
    "Croatian": "hr",
    "Bulgarian": "bg",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Icelandic": "is",
    "Filipino": "fil",
    "Swahili": "sw",
    "Mongolian": "mn",
    "Persian": "fa",
    "Kazakh": "kk",
    "Uzbek": "uz",
}


def is_lack_language(item: dict, need_lang: list = None) -> bool:
    flag = False
    
    for lang in need_lang:
        if item.get(lang, "") == "":
            flag = True
            return flag
    
    return flag
