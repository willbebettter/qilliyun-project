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

CUSTOM_CSS = """
.gradio-container {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%) !important;
    min-height: 100vh;
}
#main-title {
    text-align: center;
    background: linear-gradient(90deg, #00d2ff, #7b2ff7, #f107a3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    margin-bottom: 0 !important;
}
#subtitle { text-align: center; color: #8892b0 !important; margin-top: 0 !important; }
.sidebar-panel, .preview-panel {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
#preview-window {
    border: 2px solid rgba(0,210,255,0.35) !important;
    border-radius: 12px !important;
    background: rgba(0,0,0,0.25) !important;
    min-height: 420px !important;
}
footer { display: none !important; }
"""

NO_PREVIEW = "*等待生成… 素材图将在此处实时预览*"


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
    """去掉回复中的长 URL，引导用户看预览窗口。"""
    text = re.sub(r"https?://\S+", "", reply).strip()
    if text:
        return text + "\n\n✅ 素材已生成，请在右侧预览窗口查看。"
    return "✅ 素材已生成，请在右侧预览窗口查看。"


def _process_image(img_url: str | None, prompt: str) -> tuple[str | None, str, str | None]:
    """下载远程图到本地，返回 (本地路径, 预览说明, 下载路径)。"""
    if not img_url:
        return None, NO_PREVIEW, None
    local_path = download_image(img_url, prompt)
    if not local_path:
        return img_url, f"⚠️ 预览加载中（远程）\n\n{img_url}", None
    session.current_image = local_path
    return local_path, _preview_info(local_path, prompt), local_path


def respond(message, history):
    if not message.strip():
        return history, "", None, NO_PREVIEW, gr.update(interactive=False), session.gallery

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


def on_custom_save(filename: str):
    if not filename.strip():
        return gr.update(), "⚠️ 请输入文件名"
    saved = save_image_as(session.current_image, filename.strip())
    if not saved:
        return gr.update(interactive=False), "⚠️ 当前没有可保存的图片"
    return gr.update(interactive=True, value=saved), f"✅ 已准备下载：**{Path(saved).name}**，点击「保存到本地」选择存放位置"


def on_style_change(style):
    session.style = style
    session.reset_executor()
    return f"✅ 已切换画风 → **{style}**"


def on_category_change(category):
    session.category = "" if not category or category == "（通用）" else category
    session.reset_executor()
    label = session.category or "通用"
    return f"✅ 已切换分类 → **{label}**"


def clear_memory():
    session.reset_executor()
    session.current_image = None
    return (
        [],
        None,
        NO_PREVIEW,
        gr.update(interactive=False, value=None),
        session.gallery,
        "🔄 对话记忆已清空",
        "",
    )


def random_example():
    return random.choice(EXAMPLE_PROMPTS)


def build_ui():
    with gr.Blocks(title="2D 游戏素材 AI 生成器") as demo:
        gr.Markdown("# 🎮 2D 游戏素材 AI 生成器", elem_id="main-title")
        gr.Markdown(
            "Powered by Qwen + Wanx · 生成后可在右侧实时预览，并保存到本地",
            elem_id="subtitle",
        )

        with gr.Row():
            # ── 左侧设置栏 ──
            with gr.Column(scale=1, elem_classes="sidebar-panel"):
                gr.Markdown("### ⚙️ 生成设置")
                style_dd = gr.Dropdown(
                    choices=list(STYLE_PRESETS.keys()),
                    value="像素风",
                    label="🎨 画风",
                )
                cat_dd = gr.Dropdown(
                    choices=["（通用）"] + list(CATEGORY_TEMPLATES.keys()),
                    value="（通用）",
                    label="📦 素材分类",
                )
                status_md = gr.Markdown("当前：**像素风** · **通用**")

                gr.Markdown("### 💡 快捷示例")
                with gr.Row():
                    ex_btn1 = gr.Button("⚔️ 战士", size="sm")
                    ex_btn2 = gr.Button("🧪 药水", size="sm")
                    ex_btn3 = gr.Button("🌲 场景", size="sm")
                with gr.Row():
                    ex_btn4 = gr.Button("🪙 金币", size="sm")
                    ex_btn5 = gr.Button("💀 Boss", size="sm")
                    rand_btn = gr.Button("🎲 随机", size="sm")
                clear_btn = gr.Button("🗑️ 清空对话", variant="secondary")

            # ── 中间对话区 ──
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="💬 对话",
                    height=460,
                    buttons=["copy"],
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="描述你的素材，例如：持盾的骑士角色，蓝色盔甲，待机姿势…",
                        label="素材描述",
                        scale=5,
                        lines=2,
                    )
                    send_btn = gr.Button("✨ 生成", variant="primary", scale=1)

            # ── 右侧预览 & 保存区 ──
            with gr.Column(scale=2, elem_classes="preview-panel"):
                gr.Markdown("### 🖼️ 素材在线预览")
                preview = gr.Image(
                    label="",
                    height=420,
                    show_label=False,
                    interactive=False,
                    elem_id="preview-window",
                )
                preview_info = gr.Markdown(NO_PREVIEW)

                gr.Markdown("### 💾 保存到本地")
                save_filename = gr.Textbox(
                    label="自定义文件名（可选）",
                    placeholder="例如：knight_sprite.png，留空则使用自动命名",
                )
                with gr.Row():
                    prepare_save_btn = gr.Button("📁 准备另存为", size="sm")
                    save_btn = gr.DownloadButton(
                        "💾 保存到本地",
                        variant="primary",
                        interactive=False,
                    )
                save_status = gr.Markdown(
                    f"文件默认保存在 `{OUTPUT_DIR}`，点击「保存到本地」可在弹窗中选择任意目录"
                )

                gr.Markdown("### 📚 历史素材")
                gallery = gr.Gallery(
                    label="点击缩略图可切换预览",
                    columns=3,
                    height=180,
                    object_fit="contain",
                    allow_preview=True,
                )

        # ── 事件绑定 ──
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

        gen_outputs = [chatbot, msg_input, preview, preview_info, save_btn, gallery]
        for evt in (msg_input.submit, send_btn.click):
            evt(respond, [msg_input, chatbot], gen_outputs)

        gallery.select(
            on_gallery_select,
            outputs=[preview, preview_info, save_btn],
        )

        prepare_save_btn.click(
            on_custom_save,
            inputs=[save_filename],
            outputs=[save_btn, save_status],
        )

        clear_btn.click(
            clear_memory,
            outputs=[chatbot, preview, preview_info, save_btn, gallery, status_md, save_filename],
        )

        examples = EXAMPLE_PROMPTS
        ex_btn1.click(lambda: examples[0], outputs=[msg_input])
        ex_btn2.click(lambda: examples[1], outputs=[msg_input])
        ex_btn3.click(lambda: examples[2], outputs=[msg_input])
        ex_btn4.click(lambda: examples[3], outputs=[msg_input])
        ex_btn5.click(lambda: examples[4], outputs=[msg_input])
        rand_btn.click(random_example, outputs=[msg_input])

    return demo


def _theme():
    return gr.themes.Base(
        primary_hue="cyan",
        secondary_hue="purple",
        neutral_hue="slate",
    ).set(
        body_background_fill="#0f0c29",
        body_background_fill_dark="#0f0c29",
        block_background_fill="rgba(255,255,255,0.05)",
        block_background_fill_dark="rgba(255,255,255,0.05)",
        block_border_color="rgba(255,255,255,0.1)",
        block_label_text_color="#ccd6f6",
        input_background_fill="rgba(255,255,255,0.07)",
    )


def launch():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    launch()
