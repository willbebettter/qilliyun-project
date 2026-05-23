"""2D 游戏素材生成 Agent 核心模块"""

import os
import re
import warnings
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from urllib.request import urlretrieve

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

OUTPUT_DIR = Path(__file__).parent / "output"


def get_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "未找到 DASHSCOPE_API_KEY，请设置环境变量或在项目根目录创建 .env 文件：\n"
            "  DASHSCOPE_API_KEY=your_key_here"
        )
    return key


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
        f"你是专业的2D游戏素材生成助手，当前风格为「{style}」{cat_hint}。"
        "根据用户需求调用生图工具，生成契合2D游戏主题的图片素材。"
        "回复简洁友好，生成成功后告知用户图片已就绪。"
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
    """从远程 URL 下载图片到 output 目录，返回本地路径。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now():%Y%m%d_%H%M%S}_{_safe_filename(prompt)}.png"
    filepath = OUTPUT_DIR / filename
    try:
        urlretrieve(url, filepath)
        return str(filepath.resolve())
    except Exception:
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
