"""2D 游戏素材生成 Agent 核心模块"""

import os
import re
import warnings
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import dashscope
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

STYLE_PRESETS = {
    "像素风": "16-bit pixel art style, retro game aesthetic, crisp pixels",
    "卡通": "cute cartoon style, bold outlines, vibrant colors",
    "等距视角": "isometric 2D game view, top-down diagonal perspective",
    "手绘": "hand-drawn sketch style, organic lines, watercolor feel",
    "暗黑奇幻": "dark fantasy RPG style, moody lighting, gothic elements",
    "赛博朋克": "cyberpunk neon style, futuristic UI elements, glowing accents",
}

CATEGORY_TEMPLATES = {
    "角色": "2D game character sprite, full body, transparent background, {desc}",
    "道具": "2D game item icon, centered, transparent background, {desc}",
    "场景": "2D game background scene, wide composition, {desc}",
    "UI元素": "2D game UI element, clean design, {desc}",
    "怪物": "2D game enemy sprite, full body, transparent background, {desc}",
    "特效": "2D game visual effect, particle style, {desc}",
}

EXAMPLE_PROMPTS = [
    "持剑的精灵战士，绿色盔甲，待机姿势",
    "红色药水图标，玻璃瓶装，发光液体",
    "森林关卡背景，横版卷轴风格，多层视差",
    "金币UI图标，圆形，金色光泽",
    "火焰骷髅Boss，紫色火焰环绕",
    "魔法爆炸特效，蓝色粒子扩散",
]

RANDOM_PROMPTS = [
    "持剑的精灵战士，绿色盔甲，待机姿势",
    "红色药水图标，玻璃瓶装，发光液体",
    "森林关卡背景，横版卷轴风格，多层视差",
    "金币UI图标，圆形，金色光泽",
    "火焰骷髅Boss，紫色火焰环绕",
    "魔法爆炸特效，蓝色粒子扩散",
    "冰霜巨龙Boss，蓝色寒气，展翅姿势",
    "暗影刺客角色，黑色斗篷，双持匕首",
    "治疗药水，绿色玻璃瓶，气泡效果",
    "魔法卷轴道具，羊皮纸质感，金色符文",
    "城堡大厅场景，石柱拱门，火炬照明",
    "技能冷却UI图标，沙漏造型",
    "巨型蜘蛛怪物，紫色斑纹，八只眼睛",
    "雷电术特效，金色闪电链",
    "狂战士角色，双手巨斧，肌肉轮廓",
    "法力药水，蓝紫色琉璃瓶",
    "地下城洞穴场景，钟乳石，暗河",
    "生命值UI血条，红宝石质感",
    "暗黑武士Boss，重甲长刀，红色斗气",
    "火焰箭矢特效，拖尾粒子",
    "精灵弓箭手，绿色斗篷，长弓满拉",
    "护盾药水，金色光泽，菱形瓶",
    "沙漠废墟场景，金字塔残垣，风沙",
    "经验值UI进度条，蓝色水晶",
    "机械傀儡Boss，齿轮关节，蒸汽喷涌",
    "冰霜新星特效，白色冰晶扩散",
    "圣骑士角色，银白盔甲，圣光环绕",
    "宝石道具，六边形切割，七彩折射",
    "雪山之巅场景，暴风雪，冰晶",
    "背包UI格，皮革纹理",
    "地狱三头犬Boss，锁链项圈，熔岩皮肤",
    "神圣治愈特效，金色光芒降落",
    "忍者角色，夜行衣，手里剑",
    "钥匙道具，古铜色，齿纹精致",
    "海盗船甲板场景，桅杆帆布，海浪",
    "技能树UI节点，星芒连线",
    "石像鬼怪物，灰色石材，蝙蝠翅膀",
    "旋风斩特效，青色剑气旋转",
    "德鲁伊角色，鹿角头饰，自然藤蔓",
    "宝箱道具，金色镶边，打开状态",
    "浮游岛场景，瀑布悬空，云层环绕",
    "聊天框UI，半透明底，羽化边缘",
    "深海巨兽Boss，章鱼触手，生物荧光",
    "传送门特效，漩涡光效，紫色裂隙",
    "熊猫武僧角色，竹棍，中式布衣",
    "盾牌道具，鸢盾造型，徽章纹饰",
    "霓虹街道场景，赛博朋克风，全息广告牌",
    "小地图UI，圆形裁切，指南针标记",
    "吸血鬼伯爵Boss，红眼尖牙，蝙蝠群",
    "毒雾领域特效，绿色瘴气扩散",
    "小魔女角色，尖帽扫帚，星月法阵",
    "魔法书道具，翻页动画，符文飘出",
    "樱花庭院场景，日式木桥，飘落花瓣",
    "对话框UI，气泡形状，尾部箭头",
    "岩石巨人Boss，青苔覆盖，水晶矿脉",
    "陨石坠落特效，火焰尾迹，地面冲击波",
    "海盗船长角色，三角帽，弯刀钩手",
    "藏宝图道具，泛黄纸张，X标记",
    "太空站场景，科幻风格，星光舷窗",
    "任务面板UI，羊皮纸底纹，羽毛笔图标",
    "九尾妖狐Boss，火焰尾巴，魅惑紫瞳",
    "圣光护盾特效，金色六边形蜂巢",
    "机甲战士角色，合金装甲，喷射背包",
    "齿轮道具，黄铜材质，蒸汽朋克",
    "蘑菇森林场景，巨大菌伞，荧光孢子",
    "成就徽章UI，金属质感，浮雕图案",
    "深渊恶魔Boss，熔岩裂隙，黑色羽翼",
    "水龙卷特效，蓝色水纹旋转",
    "狼人角色，银灰毛发，利爪月光",
    "望远镜道具，黄铜伸缩筒，皮革包裹",
    "水墨竹林场景，中国风，飞白笔触",
    "排行榜UI，水晶底座，金色冠冕",
    "美杜莎Boss，蛇发缠绕，石化凝视",
    "光之翼特效，白色羽毛飘落",
    "哥布林商人角色，大背包，金币袋",
    "灯笼道具，中式宫灯，柔和光晕",
    "火山地狱场景，岩浆喷发，黑烟滚滚",
    "好友列表UI，头像圆形裁切，在线绿点",
    "克苏鲁触手Boss，粘液质感，眼球密布",
    "樱花散落特效，粉色花瓣飘飞",
    "大天使角色，六翼光羽，审判之剑",
    "闪电链特效，白色电光跳跃分叉",
    "魔法水晶矿道具，紫色晶体簇，发光底座",
    "沼泽湿地场景，枯树雾气，萤火点点",
    "毒液史莱姆怪物，绿色半透明，分裂增殖",
    "施法吟唱特效，符文法阵旋转扩散",
]

OUTPUT_DIR = Path(__file__).parent / "output"
CURRENT_SESSION_DIR = OUTPUT_DIR / "current_session_images"


def get_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "未找到 DASHSCOPE_API_KEY，请设置环境变量或在项目根目录创建 .env 文件：\n"
            "  DASHSCOPE_API_KEY=your_key_here"
        )
    return key


def clear_current_session_dir() -> None:
    """清空本次会话文件夹，新对话调用"""
    try:
        if CURRENT_SESSION_DIR.exists():
            for f in CURRENT_SESSION_DIR.glob("*.png"):
                f.unlink(missing_ok=True)
        CURRENT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def build_image_prompt(description: str, style: str = "像素风", category: str = "") -> str:
    style_hint = STYLE_PRESETS.get(style, STYLE_PRESETS["像素风"])
    if category and category in CATEGORY_TEMPLATES:
        base = CATEGORY_TEMPLATES[category].format(desc=description)
    else:
        base = description
    return f"{base}, {style_hint}, 2D game asset, game-ready"


def _make_generate_image_tool(style: str = "像素风", category: str = ""):
    @tool
    def generate_image(prompt1: str) -> str:
        """根据文字描述生成图片，返回2D游戏素材主题的像素风图片URL。当用户需要生成图片、画图、创作图像时使用此工具。"""
        dashscope.api_key = get_api_key()
        full_prompt = build_image_prompt(prompt1, style, category)
        full_prompt += "（注意：必须符合2D游戏风格，契合游戏素材用途）"
        rsp = dashscope.ImageSynthesis.call(
            model="wanx-v1",
            prompt=full_prompt,
            n=1,
            size="1024*1024",
        )
        if rsp.status_code == HTTPStatus.OK:
            return rsp.output.results[0].url
        return f"图片生成失败: {rsp.message}"

    return generate_image


def create_executor(style: str = "像素风", category: str = "") -> AgentExecutor:
    llm = ChatOpenAI(
        model="qwen-turbo",
        temperature=0.3,
        api_key=SecretStr(get_api_key()),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    gen_tool = _make_generate_image_tool(style, category)
    tools = [gen_tool]
    cat_hint = f"，素材类型偏向「{category}」" if category else ""
    system_msg = (
        f"你是专业的2D游戏素材生成助手，当前风格为「{style}」{cat_hint}。\n"
        "根据用户需求调用生图工具，生成契合2D游戏主题的图片素材。\n"
        "回复简洁友好，生成成功后告知用户图片已就绪。\n"
        "必须返回信息给用户，即使报错也要说明原因。"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
        verbose=False,
    )


def extract_image_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s\)\]\"']+\.(?:png|jpg|jpeg|webp|gif)", text, re.I)
    if match:
        return match.group(0)
    match = re.search(r"https?://[^\s\)\]\"']+", text)
    return match.group(0) if match else None


def chat(executor: AgentExecutor, user_input: str) -> tuple[str, str | None]:
    result = executor.invoke({"input": user_input})
    output = result.get("output", str(result))
    return output, extract_image_url(output)


def _safe_filename(text: str, max_len: int = 24) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return (cleaned or "asset")[:max_len]


def download_image(url: str, prompt: str = "asset") -> str | None:
    """从远程 URL 下载图片到本次会话文件夹，返回本地路径。带多策略重试。"""
    import time as _time
    import requests as _requests

    CURRENT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    safe_prompt = _safe_filename(prompt)[:30] if prompt else "asset"
    filename = f"{datetime.now():%Y%m%d_%H%M%S}_{safe_prompt}.png"
    filepath = CURRENT_SESSION_DIR / filename

    strategy_list = [
        {
            "name": "browser_full",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.9",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.aliyun.com/",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
            }
        },
        {
            "name": "browser_simple",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://dashscope.aliyuncs.com/",
            }
        },
    ]

    try:
        api_key = get_api_key()
        if api_key:
            strategy_list.insert(0, {
                "name": "auth_headers",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": "https://dashscope.aliyuncs.com/",
                    "Authorization": f"Bearer {api_key}",
                }
            })
    except Exception:
        pass

    for strategy in strategy_list:
        for attempt in range(4):
            try:
                resp = _requests.get(url, timeout=45, headers=strategy["headers"], allow_redirects=True, stream=True)
                if resp.status_code == 403 and attempt < 3:
                    _time.sleep(3 * (attempt + 1))
                    continue
                if resp.status_code == 429 and attempt < 3:
                    _time.sleep(6 * (attempt + 1))
                    continue
                resp.raise_for_status()
                content = resp.content
                if len(content) < 500:
                    if attempt < 3:
                        _time.sleep(2 * (attempt + 1))
                        continue
                    continue
                filepath.write_bytes(content)
                saved_len = filepath.stat().st_size
                if saved_len < 500:
                    filepath.unlink(missing_ok=True)
                    if attempt < 3:
                        _time.sleep(3 * (attempt + 1))
                        continue
                    continue
                return str(filepath.resolve())
            except Exception:
                if filepath.exists():
                    filepath.unlink(missing_ok=True)
                if attempt < 3:
                    _time.sleep(2 * (attempt + 1))

    return None


def save_image_as(source_path: str | None, filename: str) -> str | None:
    """按用户指定文件名另存一份，供下载按钮使用。"""
    if not source_path or not Path(source_path).is_file():
        return None
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = _safe_filename(filename, max_len=40)
    if not name.lower().endswith(".png"):
        name += ".png"
    dest = OUTPUT_DIR / name
    if dest.resolve() != Path(source_path).resolve():
        dest.write_bytes(Path(source_path).read_bytes())
    return str(dest.resolve())