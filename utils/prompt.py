import re

from utils.languages import ISO

NEED_LANG = [
    "Chinese", "English", "Spanish", "Japanese", "Korean", "Thai", "Arabic","German", "French", "Italian", "Russian", "Portuguese", "Indonesian",
    "Hindi", "Telugu", "Tamil", "Urdu", "Vietnamese", "Malay", "Norwegian", "Swedish", "Finnish", "Danish", "Dutch", "Catalan", "Hebrew",
    "Greek", "Hungarian", "Polish", "Czech", "Slovak", "Romanian", "Slovenian", "Croatian", "Bulgarian", "Turkish", "Ukrainian", "Icelandic", 
    "Filipino", "Swahili", "Mongolian", "Persian", "Kazakh", "Uzbek"
    ]


STYLE = [
    "sad", "chat", "calm", "angry", "sorry", "gentle", "serious", "fearful", "excited", "envious", "lyrical", "hopeful", "cheerful", "newscast", 
    "friendly", "shouting", "depressed", "terrified", "assistant", "unfriendly", "whispering", "empathetic", "disgruntled", "embarrassed", 
    "chat-casual", "conversation", "affectionate", "poetry-reading", "livecommercial", "newscast-formal", "customerservice", "newscast-casual", 
    "sports-commentary", "narration-relaxed", "advertisement-upbeat", "documentary-narration", "narration-professional", 
    "sports-commentary-excited"
]

SCENE = [
     "chat-casual", "conversation", "livecommercial", "sorry", "speech", "broadcast", "interviews"
]


PROMPT_PREFIX = "Translate the following English sentence into the Chinese. Return the translation alongside the original English sentence. Ensure the translation retains the original meaning and follows the word order of the English sentence, while maintaining grammatical correctness and fluency. Provide the translations in the following format, including the original English sentence without any additional content:"
STYLE_SUFFIX = "Style: [Choose one from: " + ', '.join(STYLE) + ']'
SCENE_SUFFIX = "Scene: [Choose one from: " + ', '.join(SCENE) + ']'

PATTERN_RESPONSE = re.compile(r'\*\*(.*?):\*\*')
PATTERN_SPECIAL = re.compile(r'[*>/"\'\\\.\[\]\(\)|:_;&😌😀-🙏🌀-🗿🚀-🛴🥇-🧿🧸-🧼🪀-🪙🪨-🪶🫀-🫓🫠-🫰🫳-🫶🫷-🫺🫻-🫾→←↑↓↔↕↖↗↘↙]|[^a-zA-Z0-9,\s]')


SST_PROMPT = {
    "zh-cn": {
        "en":  r"""你是同声传译员，任务是根据原文逐步以英文口播译文，遵守以下规则：
【增量翻译】
原文逐步增加时，只追加新的译文内容，不修改或修正之前已输出的译文。

【输出格式】
每次新增译文后，严格按以下格式输出：

[已累积的原文内容]：<当前累计的原文>
[已口播译文]：<当前累计的译文>

【切分原则】
    1. **越快越好**：一遇到自然停顿或语义边界立即断句。  
     - 专有名词 / 机构名称可单独成段，先行播译。  
     - 动作（宣布、发布等）或时间点（昨天、十月一号）出现即单独成段。 
     - **绝不翻译口头填充**：诸如“哦、嗯、啊、呢、那个”等语气词 **在译文中一律省略**。 
    2. 单段**不超过 ≈8 汉字或≈2 秒语音**，防止译文滞后。  
    3. 中文标点归段尾；英文译文不重复中文标点。
【译文要求】
    0. 语气词处理：
        • 若语气词（哦、嗯、啊、呢、那个 等）单独成段，须译出对应简单口语（Oh, Hmm, Uh-huh 等）；
        • 若与其他内容同段，则在译文中省略。
	1. 极度凝练：能省冠词、系动词就省；删除冗余。
	2. 段段可连读：全部译文顺序拼接后须自然流畅、语义完整。
	3. 核心信息完整：时间、主体、数量等关键信息不得缺失。
	4. 已输出译文不可修改，只能追加。
	5. 疑问句压缩不得破坏自然语序，优先用 “Today’s …?” 等母语者可接受的最短形式。

示例 1:
输入: 
我现在开始说第一句话，今天的天气怎么样？明天的天气不错，今天是星期四。
输出：
[已累积的原文内容]：我现在  
[已口播译文]：Now

[已累积的原文内容]：开始说  
[已口播译文]：start

[已累积的原文内容]：第一句话，  
[已口播译文]：my first line,

[已累积的原文内容]：今天的天气怎么样？  
[已口播译文]：Today’s weather?

[已累积的原文内容]：明天的天气不错，  
[已口播译文]：Tomorrow looks good,

[已累积的原文内容]：今天是  
[已口播译文]：Today is

[已累积的原文内容]：星期四。  
[已口播译文]：Thursday.

示例 2:
输入: 
是吧行行，对对对，您您考虑虑比较周全。那个什么姐，就是那个上次那个就是那个货运物流单号，就是录入，包括查询那个您都后来都。
输出：
[已累积的原文内容]：是吧行行，  
[已口播译文]：Right,

[已累积的原文内容]：对对对，  
[已口播译文]：Yeah,

[已累积的原文内容]：您您考虑  
[已口播译文]：You considered

[已累积的原文内容]：比较周全。  
[已口播译文]：thoroughly.

[已累积的原文内容]：那个什么姐，  
[已口播译文]：Ma’am,

[已累积的原文内容]：就是那个  
[已口播译文]：about that

[已累积的原文内容]：上次那个  
[已口播译文]：last

[已累积的原文内容]：就是那个货运物流单号，  
[已口播译文]：freight number,

[已累积的原文内容]：就是录入，  
[已口播译文]：you entered it

[已累积的原文内容]：包括查询那个您都后来都。  
[已口播译文]：and later checked it.

示例 3:
输入: 
哦，我之前的话打过您那边的幺五二的这个号，
输出: 
[已累积的原文内容]：哦，  
[已口播译文]：Oh,

[已累积的原文内容]：我之前的话  
[已口播译文]：I

[已累积的原文内容]：打过您那边的  
[已口播译文]：called your

[已累积的原文内容]：幺五二的  
[已口播译文]：152

[已累积的原文内容]：这个号，  
[已口播译文]：number earlier,"""
    },
    "en": {
        "zh-cn": r"""
"""
    }
}

TERMS_PROMPT = {
    "system": r"""你是一名中文 ASR 专业术语抽取专家和多语种翻译专家，你需要从我给你的原文文本和对应翻译文本中抽取专业术语，只返回符合下列 JSON Schema 的内容，若无热词返回 []：
<schema>
{
  "type": "array",
  "items": { "type": "string", "maxLength": 8 }
}
</schema>
输出必须合法 JSON，不得包含注释、换行或解释。""",
    "user": r"""请按出现顺序提取下列类别词组（排除序数短语、泛指机关）：
1) 品牌/产品名 2) 人名 3) 组织名(专指) 4) 事件名
5) 商品/服务名 6) 缩写或代号 7) 行业特定名称 8) 地名
仅保留原文出现且≤8字的短语；无热词请返回 []。

示例1：
输入：
{"zh-cn": "双鱼座和魔蝎座配吗？", "en": "Are Pisces and Capricorn compatible?"}
输出：
{"term": {"zh-cn": {"en": [["双鱼座", "Pisces"], ["魔蝎座", "Capricorn"]]}}}

示例2：
输入：
{"zh-cn": "流动疫苗接种车服务到门口湖北日报讯为方便老年人接种新冠疫苗12月17日", "en": "Mobile vaccination vehicles reach people's doorsteps for convenience, reported by Hubei Daily on December 17 for elder citizens to receive COVID-19 vaccines."}
输出：
{"term": {"zh-cn": {"en": [["流动疫苗接种车", "mobile vaccination vehicle"], ["湖北日报", "Hubei Daily"]]}}}

示例3：
输入：
{"zh-cn": "探索实行党风廉政建设第一责任人述责制度。", "en": "Explore the implementation of the accountability system for the primary responsible person in Party conduct and integrity construction."}
输出：
{"term": {"zh-cn": {"en": [["党风廉政建设", "Party conduct and integrity construction"]]}}}

示例4：
输入：
{"zh-cn": "根据国务院办公厅关于转发人力资源社会保障部财政部城镇企业职工基本养老保险关系", "en": "According to the General Office of the State Council on forwarding the Ministry of Human Resources and Social Security and the Ministry of Finance's Basic Pension Insurance Relationship for Urban Enterprise Employees."}
输出：
{"term": {"zh-cn": {"en": [["国务院办公厅", "General Office of the State Council"], ["人力资源社会保障部", "Ministry of Human Resources and Social Security"], ["财政部", "Ministry of Finance"], ["城镇企业职工基本养老保险关系", "Basic Pension Insurance Relationship for Urban Enterprise Employees"]]}}}

示例5：
输入：
{"zh-cn": "目前已有多个国家向我们提出了选派航天员参加中国空间站飞行任务的需求", "en": "Several countries have expressed the need to send astronauts to participate in missions to the China Space Station."}
输出：
{"term": {"zh-cn": {"en": [["中国空间站", "China Space Station"]]}}}

示例6：
输入：
{"zh-cn": "并插入了使得猪心脏可以更好适应人体免疫系统的基因这也是全球首例转基因猪心脏移植手术", "en": "The genes were inserted to allow the pig heart to better adapt to the human immune system, marking the world's first genetically modified pig heart transplant surgery."}
输出：
{"term": {"zh-cn": {"en": [["转基因猪心脏移植手术", "genetically modified pig heart transplant surgery"]]}}}

示例7：
输入：
{"zh-cn": "美兰机场开通的首条国际货运定期航线以上由最头条播报", "en": "The first scheduled international cargo route launched by Meilan Airport is reported by the top news."}
输出：
{"term": {"zh-cn": {"en": [["美兰机场", "Meilan Airport"], ["国际货运", "international cargo"], ["定期航线", "scheduled route"]]}}}

示例8：
输入：
{"zh-cn": "我住在深圳市", "en": "I live in ShenZhen currently."}
输出：
{"term": {"zh-cn": {"en": [["深圳市", "ShenZhen"]]}}}

示例9：
输入：
{"zh-cn": "我们在AI时代"}
输出：
{"term": None}

输入：
{"zh-cn": "{transcription}", "en": "{translation}"}
"""
}

def get_prompted_text(text_in: str, src_lang: str = "English") -> str:
    prompt_suffix = ': \n'.join(NEED_LANG) + ": "
    
    prompt_prefix = PROMPT_PREFIX
    for lang in NEED_LANG:
        if lang not in prompt_prefix:
            continue
        prompt_prefix = prompt_prefix.replace(lang, src_lang)
    
    text = f"{prompt_prefix}\n\n{src_lang}: {text_in}\n{prompt_suffix}\n{STYLE_SUFFIX}\n{SCENE_SUFFIX}"
    return text.strip()



def response_to_dict(response: str) -> dict:
    response = PATTERN_RESPONSE.sub(r'\1:', response)
    dump_item = {}
    current_language = None
    current_text = ''

    for line in response.splitlines():
        splited_line = line.split(':', 1)
        if len(splited_line) == 2:
            lang = splited_line[0].strip()
            if lang in ISO:
                if current_language:
                    dump_item[ISO[current_language]] = current_text.replace('\n', ' ').strip()
                current_language = lang
                current_text = splited_line[1]
            else:
                current_text += f' {line}'
        else:
            current_text += f' {line}'
    
    if not current_language:
        return {}
    
    dump_item[ISO[current_language]] = current_text.replace('\n', ' ').strip()
    
    for special_key in ("style", "scene"):
        if dump_item.get(special_key):
            item = dump_item[special_key].split('\n', 1)[0]
            dump_item[special_key] = PATTERN_SPECIAL.sub('', item).strip().lower()
    
    dump_item[ISO[current_language]] = current_text.strip()
    return dump_item




