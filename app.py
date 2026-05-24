"""Gradio Web 可视化界面"""

import random
import re
import time
from pathlib import Path

import gradio as gr
import requests

from core import (
    CATEGORY_TEMPLATES,
    EXAMPLE_PROMPTS,
    OUTPUT_DIR,
    RANDOM_PROMPTS,
    STYLE_PRESETS,
    chat,
    create_executor,
    download_image,
    get_api_key,
)

_CSS_PATH = Path(__file__).parent / "style.css"

NO_PREVIEW = "🎨 暂无生成的素材\n\n*在左侧输入描述后点击「生成」开始创作*"


class Session:
    def __init__(self):
        self.style = "像素风"
        self.category = ""
        self.executor = None
        self.history: list[tuple[str, str, str | None]] = []

    def reset_executor(self):
        self.executor = create_executor(self.style, self.category)

    def ensure_executor(self):
        if self.executor is None:
            self.reset_executor()


session = Session()


def _strip_urls(reply: str) -> str:
    text = re.sub(r"https?://\S+", "", reply).strip()
    return text


def _build_final_prompt(user_prompt: str, style: str, category: str) -> str:
    """将用户的提示词和风格/分类设置融合后返回。"""
    style_hint = STYLE_PRESETS.get(style, "")
    cat_template = CATEGORY_TEMPLATES.get(category, "")
    if category and cat_template:
        base = cat_template.replace("{desc}", user_prompt.strip())
    else:
        base = user_prompt.strip()
    if not base.endswith("。"):
        base = base.rstrip(".,。") + "，"
    if style_hint:
        base = base + f"风格要求：{style_hint}。"
    return base


def _download_for_save(img_url: str) -> bytes | None:
    """直接下载图片字节数据，用于保存。返回 bytes 或 None。"""
    strategy_list = []

    try:
        api_key = get_api_key()
        if api_key:
            strategy_list.append({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://dashscope.aliyuncs.com/",
                "Authorization": f"Bearer {api_key}",
            })
    except Exception:
        pass

    strategy_list.append({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.aliyun.com/",
    })

    strategy_list.append({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
    })

    for headers in strategy_list:
        for attempt in range(3):
            try:
                resp = requests.get(img_url, timeout=30, headers=headers, allow_redirects=True)
                if resp.status_code == 403 and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                if resp.status_code == 429 and attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                if len(resp.content) < 500:
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                        continue
                    break
                return resp.content
            except Exception:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))

    return None


def _toggle_send_btn(text: str):
    has_content = bool(text and text.strip())
    return gr.update(interactive=has_content)


def _format_ai_response(reply: str, img_url: str | None, style: str, category: str) -> str:
    """格式化 AI 回复，包含可点击的图片链接。"""
    style_label = style
    category_label = category or "通用"
    context_line = f"🎨 画风（可自定义） **{style_label}** · 📂 分类（可自定义） **{category_label}**"

    if img_url:
        link_markdown = f"\n\n🖼️ **生成结果**：[点击在新窗口查看图片]({img_url})"
        return f"{reply}\n\n{context_line}{link_markdown}"
    else:
        return f"{reply}\n\n{context_line}\n\n⚠️ 未获取到图片 URL，请重试"


def respond_generator(message, history):
    """带加载动画的响应函数（生成器模式）。"""
    if not message.strip():
        return

    final_prompt = _build_final_prompt(message, session.style, session.category)

    loading_user = message
    loading_bot = (
        "🎨 **AI 正在生成素材中…**  \n\n"
        f"（融合提示词：{final_prompt[:80]}{'…' if len(final_prompt) > 80 else ''}）  \n\n"
        '<span class="loading-dots"><span></span><span></span><span></span></span>'
    )

    yield (
        history + [(loading_user, loading_bot)],
        "",
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        NO_PREVIEW,
        None,
        "",
    )

    try:
        session.ensure_executor()
        reply, img_url = chat(session.executor, final_prompt)

        safe_reply = _strip_urls(reply)
        formatted = _format_ai_response(safe_reply, img_url, session.style, session.category)

        session.history.append((message, formatted, img_url))

        has_url = img_url is not None

        info_text = (
            f"✅ 素材已生成！\n\n"
            f"描述：{message}\n\n"
            f"风格：{session.style} · 分类：{session.category or '通用'}\n\n"
            f"点击下方「💾 下载图片到本地」按钮保存"
            if img_url else
            f"⚠️ 未获取到图片 URL\n\n描述：{message}\n\n请尝试重新生成"
        )

        yield (
            history + [(message, formatted)],
            "",
            gr.update(interactive=has_url),
            gr.update(interactive=has_url),
            gr.update(interactive=True),
            info_text,
            img_url,
            message,
        )

    except Exception as e:
        error_msg = f"❌ 生成异常：{str(e)}\n\n请检查网络或 API 配置后重试。"
        yield (
            history + [(message, error_msg)],
            "",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            f"❌ 发生错误\n\n{str(e)[:100]}",
            None,
            "",
        )


def _save_handler(img_url: str, prompt: str) -> str:
    """下载按钮回调：下载图片到本地，返回保存状态文字。"""
    if not img_url:
        return "⚠️ 没有可下载的图片，请先生成素材"
    local_path = download_image(img_url, prompt)
    if local_path and Path(local_path).is_file():
        return f"✅ 已保存到：{Path(local_path).name}"
    img_bytes = _download_for_save(img_url)
    if img_bytes:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", (prompt or "asset").strip())[:24] or "asset"
        filename = f"asset_{safe}.png"
        filepath = OUTPUT_DIR / filename
        filepath.write_bytes(img_bytes)
        return f"✅ 已保存到：{filepath.name}"
    return "⚠️ 下载失败，请检查网络后重试"


def on_style_change(style):
    session.style = style
    session.reset_executor()
    return f"✅ 已切换画风 → **{style}**"


def on_category_change(category):
    session.category = "" if not category or category == "（通用）" else category
    session.reset_executor()
    label = session.category or "通用"
    return f"✅ 已切换分类 → **{label}**"


def new_conversation():
    session.reset_executor()
    session.history.clear()
    return (
        [],
        "",
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        NO_PREVIEW,
        None,
        "",
    )


def quick_generate(prompt_text: str, history):
    if not prompt_text.strip():
        return
    yield from respond_generator(prompt_text, history)


def random_example():
    return random.choice(RANDOM_PROMPTS)


def build_ui():
    with gr.Blocks(title="2D 游戏素材 AI 生成器") as demo:

        gr.HTML("""
<div id="bg-particles">
  <div class="p"></div><div class="p"></div><div class="p"></div>
  <div class="p"></div><div class="p"></div><div class="p"></div>
  <div class="p"></div><div class="p"></div>
</div>
""")

        gr.HTML("""
<script>
(function() {
  var tid = setInterval(function() {
    document.querySelectorAll('.settings-row .wrap, .settings-row .gr-dropdown').forEach(function(el) {
      el.style.overflow = 'visible';
    });
  }, 500);
  setTimeout(function() { clearInterval(tid); }, 15000);
})();
</script>
""")

        gr.Markdown("# 🎮 2D 游戏素材 AI 生成器", elem_id="main-title")
        gr.Markdown(
            "Powered by Qwen + Wanx · 图片链接直接在对话中展示，点击即可查看",
            elem_id="subtitle",
        )

        with gr.Row(elem_classes="settings-row"):
            with gr.Column(scale=1):
                gr.Markdown("⚙️ **风格设置**", elem_classes="section-label")
                style_dd = gr.Dropdown(
                    choices=list(STYLE_PRESETS.keys()),
                    value="像素风",
                    label="🎨 画风（可自定义）",
                )
            with gr.Column(scale=1):
                gr.Markdown("📂 **素材分类**", elem_classes="section-label")
                cat_dd = gr.Dropdown(
                    choices=["（通用）"] + list(CATEGORY_TEMPLATES.keys()),
                    value="（通用）",
                    label="📦 素材分类（可自定义）",
                )
            with gr.Column(scale=2):
                gr.Markdown("⚡ **快捷生成**", elem_classes="section-label")
                with gr.Row():
                    ex_btn1 = gr.Button("⚔️ 战士", size="sm", variant="secondary")
                    ex_btn2 = gr.Button("🧪 药水", size="sm", variant="secondary")
                    ex_btn3 = gr.Button("🌲 场景", size="sm", variant="secondary")
                    ex_btn4 = gr.Button("🪙 金币", size="sm", variant="secondary")
                    ex_btn5 = gr.Button("💀 Boss", size="sm", variant="secondary")
                    rand_btn = gr.Button("🎲 随机 (100+精美提示词模板)", size="sm", variant="secondary")
            with gr.Column(scale=1):
                status_md = gr.Markdown("当前：**像素风** · **通用**")
                new_btn = gr.Button("🆕 新建对话", variant="secondary")

        latest_img_url = gr.Textbox(label="", visible=False, lines=1)
        latest_prompt = gr.Textbox(label="", visible=False, lines=1)

        with gr.Row(elem_classes="main-row"):
            with gr.Column(scale=5, elem_classes="chat-panel"):
                gr.Markdown("### 💬 对话区")
                chatbot = gr.Chatbot(
                    value=[],
                    placeholder="输入素材描述，点击 ✨ 生成 开始创作你的2D游戏素材",
                    height=560,
                    buttons=["copy"],
                    show_label=False,
                )
                msg_input = gr.Textbox(
                    placeholder="描述你的素材，例如：持盾的骑士角色，蓝色盔甲，待机姿势…",
                    label="素材描述",
                    lines=2,
                    elem_id="chat-input",
                )
                send_btn = gr.Button(
                    "✨ 生成",
                    variant="primary",
                    interactive=False,
                    elem_id="send-btn-wrap",
                )
                gr.Markdown(
                    "按 **Enter** 发送 · 点击顶部快捷按钮可一键快速生成",
                    elem_classes="chat-footer-area",
                )

            with gr.Column(scale=3, elem_classes="preview-panel"):
                gr.Markdown("### 💾 保存到本地")
                gr.Markdown(
                    "生成后点击下方按钮下载图片到本地",
                    elem_classes="section-label",
                )
                save_btn = gr.Button(
                    "💾 下载图片到本地",
                    variant="primary",
                    interactive=False,
                    size="lg",
                )
                download_status = gr.Markdown(
                    "请先在左侧生成素材，生成后点击上方按钮下载"
                )

                gr.Markdown("### 📌 当前状态")
                preview_info = gr.Markdown(NO_PREVIEW)

        style_dd.change(on_style_change, [style_dd], [status_md]).then(
            lambda s, c: f"当前：**{s}** · **{c if c != '（通用）' else '通用'}**",
            [style_dd, cat_dd],
            [status_md],
        )
        cat_dd.change(on_category_change, [cat_dd], [status_md]).then(
            lambda s, c: f"当前：**{s}** · **{c if c != '（通用）' else '通用'}**",
            [style_dd, cat_dd],
            [status_md],
        )

        msg_input.change(_toggle_send_btn, [msg_input], [send_btn])

        gen_outputs = [
            chatbot, msg_input, save_btn, download_status, send_btn, preview_info,
            latest_img_url, latest_prompt,
        ]

        send_btn.click(
            lambda: gr.update(interactive=False),
            outputs=[send_btn],
        ).then(
            respond_generator,
            [msg_input, chatbot],
            gen_outputs,
        )

        msg_input.submit(
            lambda: gr.update(interactive=False),
            outputs=[send_btn],
        ).then(
            respond_generator,
            [msg_input, chatbot],
            gen_outputs,
        )

        save_btn.click(
            _save_handler,
            [latest_img_url, latest_prompt],
            [download_status],
        )

        new_btn.click(
            new_conversation,
            outputs=[
                chatbot, msg_input, save_btn, download_status, send_btn, preview_info,
                latest_img_url, latest_prompt,
            ],
        )

        qg_outputs = [
            chatbot, msg_input, save_btn, download_status, send_btn, preview_info,
            latest_img_url, latest_prompt,
        ]

        for btn, idx in zip([ex_btn1, ex_btn2, ex_btn3, ex_btn4, ex_btn5], range(5)):
            btn.click(
                lambda i=idx: EXAMPLE_PROMPTS[i],
                outputs=[msg_input],
            ).then(
                lambda: gr.update(interactive=False),
                outputs=[send_btn],
            ).then(
                quick_generate,
                [msg_input, chatbot],
                qg_outputs,
            )

        rand_btn.click(
            random_example,
            outputs=[msg_input],
        ).then(
            lambda: gr.update(interactive=False),
            outputs=[send_btn],
        ).then(
            quick_generate,
            [msg_input, chatbot],
            qg_outputs,
        )

    return demo


def _theme():
    return gr.themes.Base(
        primary_hue="violet",
        secondary_hue="blue",
        neutral_hue="slate",
    ).set(
        body_background_fill="#030308",
        body_background_fill_dark="#030308",
        block_background_fill="rgba(255,255,255,0.03)",
        block_background_fill_dark="rgba(255,255,255,0.03)",
        block_border_color="rgba(255,255,255,0.06)",
        block_label_text_color="#a5b4fc",
        input_background_fill="rgba(255,255,255,0.04)",
    )


def launch():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    css_text = _CSS_PATH.read_text(encoding="utf-8") if _CSS_PATH.exists() else ""

    try:
        session.reset_executor()
    except EnvironmentError as e:
        demo = gr.Blocks(title="配置错误")
        with demo:
            gr.Markdown(f"# ⚠️ 配置错误\n\n```\n{e}\n```")
        demo.launch()
        return

    demo = build_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=_theme(),
        css=css_text,
    )


if __name__ == "__main__":
    launch()
