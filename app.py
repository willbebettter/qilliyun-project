"""Gradio Web 可视化界面"""

import random
import re
from pathlib import Path

import gradio as gr

from core import (
    CATEGORY_TEMPLATES,
    EXAMPLE_PROMPTS,
    OUTPUT_DIR,
    STYLE_PRESETS,
    chat,
    create_executor,
    download_image,
    save_image_as,
)

_CSS_PATH = Path(__file__).parent / "style.css"

NO_PREVIEW = "🎨 素材将在此处实时预览\n\n*在左侧输入描述后点击「生成」开始创作*"


class Session:
    def __init__(self):
        self.style = "像素风"
        self.category = ""
        self.executor = None
        self.gallery: list[tuple[str, str]] = []
        self.current_image: str | None = None

    def reset_executor(self):
        self.executor = create_executor(self.style, self.category)

    def ensure_executor(self):
        if self.executor is None:
            self.reset_executor()


session = Session()


def _preview_info(local_path: str | None, prompt: str = "") -> str:
    if not local_path:
        return NO_PREVIEW
    p = Path(local_path)
    size_kb = p.stat().st_size // 1024 if p.is_file() else 0
    return (
        f"**{p.name}**  \n"
        f"尺寸 1024×1024 · {size_kb} KB  \n"
        f"描述：{prompt or '—'}  \n"
        f"💡 点击图片可全屏查看"
    )


def _clean_reply(reply: str) -> str:
    text = re.sub(r"https?://\S+", "", reply).strip()
    if text:
        return text + "\n\n✅ 素材已生成，请在右侧预览窗口查看。"
    return "✅ 素材已生成，请在右侧预览窗口查看。"


def _process_image(img_url: str | None, prompt: str) -> tuple[str | None, str, str | None]:
    if not img_url:
        return None, NO_PREVIEW, None
    local_path = download_image(img_url, prompt)
    if not local_path:
        return None, "⚠️ 图片下载失败，请重试", None
    session.current_image = local_path
    return local_path, _preview_info(local_path, prompt), local_path


def respond(message, history):
    if not message.strip():
        return history, "", None, NO_PREVIEW, gr.update(interactive=False), session.gallery, gr.update(interactive=True)

    session.ensure_executor()
    try:
        reply, img_url = chat(session.executor, message)
    except Exception as e:
        reply, img_url = f"❌ 生成失败: {e}", None

    preview_path, info, download_path = _process_image(img_url, message)
    if preview_path and img_url:
        session.gallery = [(preview_path, message)] + session.gallery[:11]
        reply = _clean_reply(reply) if not reply.startswith("❌") else reply

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    has_image = download_path is not None
    return (
        history,
        "",
        preview_path,
        info,
        gr.update(interactive=has_image, value=download_path),
        session.gallery,
        gr.update(interactive=True),
    )


def on_gallery_select(evt: gr.SelectData):
    if evt.index is None or evt.index >= len(session.gallery):
        return None, NO_PREVIEW, gr.update(interactive=False)
    local_path, caption = session.gallery[evt.index]
    session.current_image = local_path
    return (
        local_path,
        _preview_info(local_path, caption),
        gr.update(interactive=True, value=local_path),
    )


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
    session.current_image = None
    return (
        [],
        None,
        NO_PREVIEW,
        gr.update(interactive=False, value=None),
        session.gallery,
        "🔄 已新建对话",
    )


def random_example():
    return random.choice(EXAMPLE_PROMPTS)


def _fill_example(idx: int):
    def _fn():
        return EXAMPLE_PROMPTS[idx]
    return _fn


def build_ui():
    with gr.Blocks(title="2D 游戏素材 AI 生成器") as demo:
        gr.Markdown("# 🎮 2D 游戏素材 AI 生成器", elem_id="main-title")
        gr.Markdown(
            "Powered by Qwen + Wanx · 生成后可在右侧实时预览，并保存到本地",
            elem_id="subtitle",
        )

        with gr.Row(elem_classes="settings-row"):
            with gr.Column(scale=1):
                style_dd = gr.Dropdown(
                    choices=list(STYLE_PRESETS.keys()),
                    value="像素风",
                    label="🎨 画风",
                )
            with gr.Column(scale=1):
                cat_dd = gr.Dropdown(
                    choices=["（通用）"] + list(CATEGORY_TEMPLATES.keys()),
                    value="（通用）",
                    label="📦 素材分类",
                )
            with gr.Column(scale=2):
                with gr.Row():
                    ex_btn1 = gr.Button("⚔️ 战士", size="sm", variant="secondary")
                    ex_btn2 = gr.Button("🧪 药水", size="sm", variant="secondary")
                    ex_btn3 = gr.Button("🌲 场景", size="sm", variant="secondary")
                    ex_btn4 = gr.Button("🪙 金币", size="sm", variant="secondary")
                    ex_btn5 = gr.Button("💀 Boss", size="sm", variant="secondary")
                    rand_btn = gr.Button("🎲 随机", size="sm", variant="secondary")
            with gr.Column(scale=1):
                status_md = gr.Markdown("当前：**像素风** · **通用**")
                new_btn = gr.Button("🆕 新建对话", variant="secondary", size="sm")

        with gr.Row(elem_classes="main-row"):
            with gr.Column(scale=5, elem_classes="chat-panel"):
                chatbot = gr.Chatbot(
                    label="💬 对话",
                    value=[],
                    placeholder="输入素材描述，点击 ✨ 生成 开始创作你的2D游戏素材",
                    height=540,
                    buttons=["copy"],
                    show_label=True,
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
                    elem_id="send-btn-wrap",
                )
                gr.Markdown(
                    "按 **Enter** 发送 · 点击顶部快捷按钮可自动填充示例",
                    elem_classes="chat-footer-area",
                )

            with gr.Column(scale=3, elem_classes="preview-panel"):
                gr.Markdown("### 🖼️ 素材在线预览")
                preview = gr.Image(
                    label="",
                    height=380,
                    show_label=False,
                    interactive=False,
                    elem_id="preview-window",
                )
                preview_info = gr.Markdown(NO_PREVIEW)

                gr.Markdown("### 💾 保存到本地")
                save_btn = gr.DownloadButton(
                    "💾 保存到本地",
                    variant="primary",
                    interactive=False,
                )
                save_status = gr.Markdown(
                    "生成素材后点击按钮，在弹窗中选择保存位置"
                )

                gr.Markdown("### 📚 历史素材")
                gallery = gr.Gallery(
                    label="点击缩略图可切换预览",
                    columns=3,
                    height=160,
                    object_fit="contain",
                    allow_preview=True,
                )

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

        gen_outputs = [chatbot, msg_input, preview, preview_info, save_btn, gallery, send_btn]

        send_btn.click(
            lambda: gr.update(interactive=False),
            outputs=[send_btn],
        ).then(
            respond,
            [msg_input, chatbot],
            gen_outputs,
        )

        msg_input.submit(
            lambda: gr.update(interactive=False),
            outputs=[send_btn],
        ).then(
            respond,
            [msg_input, chatbot],
            gen_outputs,
        )

        gallery.select(
            on_gallery_select,
            outputs=[preview, preview_info, save_btn],
        )

        new_btn.click(
            new_conversation,
            outputs=[chatbot, preview, preview_info, save_btn, gallery, status_md],
        )

        ex_btn1.click(_fill_example(0), outputs=[msg_input])
        ex_btn2.click(_fill_example(1), outputs=[msg_input])
        ex_btn3.click(_fill_example(2), outputs=[msg_input])
        ex_btn4.click(_fill_example(3), outputs=[msg_input])
        ex_btn5.click(_fill_example(4), outputs=[msg_input])
        rand_btn.click(random_example, outputs=[msg_input])

    return demo


def _theme():
    return gr.themes.Base(
        primary_hue="violet",
        secondary_hue="blue",
        neutral_hue="slate",
    ).set(
        body_background_fill="#050510",
        body_background_fill_dark="#050510",
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
