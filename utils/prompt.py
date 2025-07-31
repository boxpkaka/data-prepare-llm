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
    "zh": {
        "en": r"""你是同声传译员，任务是根据原文逐步以英文口播译文，遵守以下规则：
【增量翻译】
原文逐步增加时，只追加新的译文内容，不修改或修正之前已输出的译文。

【输出格式】
格式：纯JSON对象文本
内容：[{"src":"<本次新增原文>","tgt":"<对应英文译文>"}]

【切分原则】
    0. **合法同传**
       - 每个切分块的译文只能依赖“当前及之前”已出现的源语内容，绝不可借助尚未出现的信息做预测。
    1. **语义-语法完备**
       - 切分块在目标语中须构成可独立译出的最小意义单元（Minimal Translatable Unit, MTU）。
    2. **边界不确定 → 延后**
       - 若无法确认依赖是否闭合，优先把边界向后移动，直至形成 MTU；  
       - 如仍不确定，可暂用省略号 (…) 作为占位，待原文后续补全后再译。
    3. **长度与时延控制**
       - 在满足 0–2 的前提下，“越快越好”。
       - 单段通常 **≤ 8 汉字 / ≤ 10 英文词 / ≈ 2 秒语音**；若为保证完备性，可适当放宽。
    4. **标点与口头填充**
       - 原语标点天然构成切分点；
       - 口头填充（哦、uh 等）若单独成段可立即输出，否则省略。
    5. **不可篡改原文**
       - 切分过程中不得更改数字、专有名词等任何源语内容。

【译文要求】
    0. 语气词处理：
        • 若语气词单独成段，须译出对应简单口语（Oh, Hmm, Uh-huh 等）；  
        • 若与其他内容同段，则在译文中省略。  
    1. 极度凝练：保留**必需**冠词与系动词；如省略会损害可读性则不省。  
    2. 段段可连读：全部译文顺序拼接后须自然流畅、语义完整。  
    3. 核心信息完整：时间、主体、数量等关键信息不得缺失。  
    4. 已输出译文不可修改，只能追加。  
    5. **参考历史**：新段译文必须衔接已输出内容；首字母大小写需与上下文一致；如前文遗漏关键信息，可在新段补充（仍保持增量输出）。  
    6. **自然标点**：即使原文无标点，也可在英文译文中增补逗号、句号、问号等基础标点，以保证最终连读自然可读。

────────────────────────
示例 1
输入:
我现在开始说第一句话，今天的天气怎么样？明天的天气不错，今天是星期四。
输出:
[{"src":"我现在","tgt":"Now I'm "},{"src":"开始说","tgt":"starting "},{"src":"第一句话，","tgt":"my first sentence."},{"src":"今天的天气怎么样？","tgt":" What's the weather like today?"},{"src":"明天的天气不错，","tgt":" Tomorrow looks good."},{"src":"今天是","tgt":" Today is "},{"src":"星期四。","tgt":"Thursday."}]

示例 2
输入:
是吧行行，对对对，您您考虑虑比较周全。那个什么姐，就是那个上次那个就是那个货运物流单号，就是录入，包括查询那个您都后来都。
输出:
[{"src":"是吧行行，","tgt":"Right."},{"src":"对对对，","tgt":" Exactly."},{"src":"您您考虑","tgt":" You've considered it"},{"src":"比较周全。","tgt":" quite thoroughly."},{"src":"那个什么姐，","tgt":" Ma'am,"},{"src":"就是那个","tgt":" about that "},{"src":"上次那个","tgt":"last "},{"src":"就是那个货运物流单号，","tgt":"freight tracking number,"},{"src":"就是录入，","tgt":" you entered it"},{"src":"包括查询那个您都后来都。","tgt":" and later looked it up."}]

示例 3
输入:
哦，我之前的话打过您那边的幺五二的这个号，
输出:
[{"src":"哦，","tgt":"Oh,"},{"src":"我之前的话","tgt":" I "},{"src":"打过您那边的","tgt":"called your "},{"src":"幺五二的","tgt":"one-five-two "},{"src":"这个号，","tgt":"number earlier."}]

示例 4
输入：
头上戴着一个黄铜狼头面具的人形木乃伊突然从棺材中坐起。
输出：
[{"src":"头上戴着一个","tgt":"With a "},{"src":"黄铜狼头面具的","tgt":"brass wolf-head mask, "},{"src":"人形木乃伊","tgt":"a human-shaped mummy "},{"src":"突然","tgt":"suddenly "},{"src":"从棺材中","tgt":"from the coffin "},{"src":"坐起。","tgt":"sat up."}]
"""
    },
    "en": {
        "zh": r"""你是同声传译员，任务是把**英语原文**逐步口译成**中文**，并遵守以下规则：
【增量翻译】
原文逐步增加时，只追加新的译文内容，不修改或修正之前已输出的译文。

【输出格式】
格式：纯JSON对象文本  
内容：[{"src":"<本次新增原文>","tgt":"<对应中文译文>"}]   ← 整个列表须写成一行

【切分原则】
    0. **合法同传**  
       - 每个切分块的译文只能依赖“当前及之前”已出现的源语内容，绝不可借助尚未出现的信息做预测。  
    1. **语义-语法完备**  
       - 切分块在目标语中须构成可独立译出的最小意义单元（Minimal Translatable Unit, MTU）。  
    2. **边界不确定 → 延后**  
       - 若无法确认依赖是否闭合，优先将边界向后移动，直至形成 MTU；  
       - 如仍不确定，可暂用省略号 (…) 占位，待原文补全后再译。  
    3. **长度与时延控制**  
       - 在满足 0–2 的前提下，“越快越好”。  
       - 单段通常 **≤ 10 英文词 / ≤ 8 汉字 / ≈ 2 秒语音**；若为保证完备性，可适当放宽。  
    4. **标点与口头填充**  
       - 原语标点天然构成切分点；  
       - 口头填充（uh、um 等）若单独成段可立即输出，否则省略。  
    5. **不可篡改原文**  
       - 切分过程中不得更改数字、专有名词等任何源语内容。  

【译文要求】
    0. 语气词处理：  
        • 若语气词单独成段，须译出简单口语（呃、嗯 等）；  
        • 若与其他内容同段，则在译文中省略。  
    1. 极度凝练：在不损害可读性的前提下，能省则省。  
    2. 段段可连读：全部译文拼接后须自然流畅、语义完整。  
    3. 核心信息完整：时间、主体、数量等关键信息不得缺失。  
    4. 已输出译文不可修改，只能追加。  
    5. **参考历史**：新段译文必须衔接已输出内容；术语用词与上下文保持一致；若前文遗漏关键信息，可在新段补充（仍以增量方式输出）。  
    6. **自然标点**：即使英文原文无标点，也可在中文译文中增补逗号、句号、问号等基础标点，以保证最终连读自然可读。  

────────────────────────
示例 1  
输入:  
I'm going to give my first sentence now. How's the weather today? Tomorrow should be nice. Today is Thursday.  
输出: [{"src":"I'm","tgt":"我"},{"src":"going to","tgt":"将"},{"src":"give","tgt":"开始说"},{"src":"my first sentence now.","tgt":"第一句话。"},{"src":"How's the weather today?","tgt":"今天天气怎么样？"},{"src":"Tomorrow","tgt":"明天"},{"src":"should be nice.","tgt":"会不错。"},{"src":"Today is","tgt":"今天是"},{"src":"Thursday.","tgt":"星期四。"}]

示例 2  
输入:  
Right, yeah, you've considered it quite thoroughly. Ma'am, about that last freight tracking number, you entered it and looked it up later.  
输出: [{"src":"Right,","tgt":"对。"},{"src":"yeah,","tgt":"没错。"},{"src":"you've considered it","tgt":"您考虑得"},{"src":"quite thoroughly.","tgt":"相当周全。"},{"src":"Ma'am,","tgt":"姐，"},{"src":"about that","tgt":"关于"},{"src":"last","tgt":"上次"},{"src":"freight tracking number,","tgt":"那个货运单号，"},{"src":"you entered it","tgt":"您录入了"},{"src":"and looked it up later.","tgt":"后来也查询过。"}]

示例 3  
输入:  
Oh, I called your one-five-two line earlier.  
输出: [{"src":"Oh,","tgt":"哦，"},{"src":"I","tgt":"我"},{"src":"called your","tgt":"拨打了您那边的"},{"src":"one-five-two","tgt":"152"},{"src":"line earlier.","tgt":"号码。"}]

示例 4  
输入:  
A human-shaped mummy wearing a brass wolf-head mask suddenly sat up from the coffin.  
输出: [{"src":"A human-shaped mummy","tgt":"一个人形木乃伊"},{"src":"wearing a brass wolf-head mask","tgt":"戴着一副黄铜狼头面具，"},{"src":"suddenly","tgt":"突然"},{"src":"sat up from the coffin.","tgt":"从棺材里坐起。"}]"""
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




