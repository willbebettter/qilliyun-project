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
/* ===== 全局基础 ===== */
.gradio-container {
    background: #06060c !important;
    min-height: 100vh;
    max-width: 100% !important;
    position: relative;
    overflow: hidden;
}

/* ===== 动效星空背景 ===== */
.gradio-container::before {
    content: '';
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(2px 2px at 10% 20%, rgba(255,255,255,0.6), transparent),
        radial-gradient(2px 2px at 25% 60%, rgba(255,255,255,0.5), transparent),
        radial-gradient(1px 1px at 40% 10%, rgba(255,255,255,0.7), transparent),
        radial-gradient(2px 2px at 55% 75%, rgba(255,255,255,0.4), transparent),
        radial-gradient(1px 1px at 70% 35%, rgba(255,255,255,0.6), transparent),
        radial-gradient(2px 2px at 85% 50%, rgba(255,255,255,0.5), transparent),
        radial-gradient(1px 1px at 15% 85%, rgba(255,255,255,0.7), transparent),
        radial-gradient(1px 1px at 50% 45%, rgba(255,255,255,0.5), transparent),
        radial-gradient(2px 2px at 65% 15%, rgba(255,255,255,0.4), transparent),
        radial-gradient(1px 1px at 90% 70%, rgba(255,255,255,0.6), transparent),
        radial-gradient(2px 2px at 5% 40%, rgba(255,255,255,0.5), transparent),
        radial-gradient(1px 1px at 35% 90%, rgba(255,255,255,0.4), transparent),
        radial-gradient(2px 2px at 75% 80%, rgba(255,255,255,0.6), transparent),
        radial-gradient(1px 1px at 45% 25%, rgba(255,255,255,0.7), transparent),
        radial-gradient(2px 2px at 20% 5%, rgba(255,255,255,0.3), transparent);
    animation: twinkle 4s ease-in-out infinite alternate;
}
@keyframes twinkle {
    0% { opacity: 0.5; }
    100% { opacity: 1; }
}

/* 流动光晕 */
.gradio-container::after {
    content: '';
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(ellipse 600px 400px at 20% 30%, rgba(120,40,200,0.08), transparent),
        radial-gradient(ellipse 500px 350px at 75% 60%, rgba(0,150,255,0.06), transparent),
        radial-gradient(ellipse 400px 300px at 50% 80%, rgba(200,20,120,0.05), transparent);
    animation: glowShift 15s ease-in-out infinite;
}
@keyframes glowShift {
    0%, 100% { transform: translate(0, 0); }
    25% { transform: translate(2%, -1%); }
    50% { transform: translate(-1%, 2%); }
    75% { transform: translate(1%, 1%); }
}

/* 确保所有面板在星空之上 */
.gradio-container > * { position: relative; z-index: 1; }

/* ===== 标题 ===== */
#main-title {
    text-align: center;
    background: linear-gradient(90deg, #00d2ff, #7b2ff7, #f107a3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    margin-bottom: 2px !important;
    letter-spacing: 2px !important;
    text-shadow: none !important;
    filter: drop-shadow(0 0 20px rgba(123,47,247,0.4));
    animation: titleGlow 3s ease-in-out infinite alternate;
}
@keyframes titleGlow {
    0% { filter: drop-shadow(0 0 20px rgba(123,47,247,0.3)); }
    100% { filter: drop-shadow(0 0 35px rgba(0,210,255,0.5)); }
}
#subtitle {
    text-align: center;
    color: #6b7fa8 !important;
    margin-top: 0 !important;
    font-size: 0.95rem !important;
    letter-spacing: 1px !important;
}

/* ===== 玻璃面板通用 ===== */
.chat-panel, .preview-panel, .settings-row {
    background: rgba(255,255,255,0.025) !important;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 18px !important;
    padding: 20px !important;
    position: relative;
    z-index: 1;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03) !important;
    transition: border-color 0.4s ease, box-shadow 0.4s ease;
}
.chat-panel:hover, .preview-panel:hover, .settings-row:hover {
    border-color: rgba(255,255,255,0.12) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 40px rgba(100,50,200,0.06), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}
.chat-panel { height: 100% !important; }
.preview-panel { height: 100% !important; }

/* 设置行 */
.settings-row {
    margin-bottom: 14px !important;
    align-items: end !important;
    padding: 14px 20px !important;
}

/* ===== 面板内部标题流光 ===== */
.preview-panel h3, .chat-panel h3, .settings-row h3 {
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
}

/* ===== 图片预览窗口 ===== */
#preview-window {
    border: 2px solid rgba(120,80,220,0.3) !important;
    border-radius: 14px !important;
    background: rgba(0,0,0,0.35) !important;
    min-height: 400px !important;
    box-shadow: 0 0 30px rgba(100,50,200,0.08), inset 0 0 60px rgba(100,50,200,0.03) !important;
    transition: border-color 0.5s ease, box-shadow 0.5s ease;
}
#preview-window:hover {
    border-color: rgba(120,80,220,0.5) !important;
    box-shadow: 0 0 40px rgba(100,50,200,0.12), inset 0 0 60px rgba(100,50,200,0.05) !important;
}

/* ===== 滚动条美化 ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track {
    background: transparent;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, rgba(120,50,200,0.4), rgba(0,150,255,0.3));
    border-radius: 3px;
    transition: background 0.3s ease;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, rgba(120,50,200,0.7), rgba(0,150,255,0.5));
}
::-webkit-scrollbar-corner { background: transparent; }

/* Firefox 滚动条 */
* {
    scrollbar-width: thin;
    scrollbar-color: rgba(120,50,200,0.4) transparent;
}

/* ===== 聊天消息气泡 ===== */
.chatbot .user {
    font-size: 15px !important;
    line-height: 1.65 !important;
}
.chatbot .bot {
    font-size: 15px !important;
    line-height: 1.65 !important;
}
.chatbot .message {
    padding: 12px 18px !important;
    border-radius: 14px !important;
    margin: 6px 0 !important;
    max-width: 90% !important;
    word-wrap: break-word !important;
    animation: msgIn 0.35s ease-out;
}
@keyframes msgIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* 用户消息气泡发光边 */
.chatbot .user .message-wrap {
    border: 1px solid rgba(120,80,220,0.25) !important;
    border-radius: 14px !important;
    box-shadow: 0 0 12px rgba(120,80,220,0.1) !important;
}
/* bot 消息气泡 */
.chatbot .bot .message-wrap {
    border: 1px solid rgba(0,180,200,0.2) !important;
    border-radius: 14px !important;
    box-shadow: 0 0 12px rgba(0,180,200,0.08) !important;
}

/* 聊天区域滚动 */
.chatbot {
    overflow-y: auto !important;
    scroll-behavior: smooth !important;
}
.chatbot .messages {
    overflow-y: auto !important;
}

/* ===== 输入框 ===== */
#chat-input textarea {
    font-size: 15px !important;
    line-height: 1.55 !important;
    padding: 12px 16px !important;
    border-radius: 12px !important;
    min-height: 60px !important;
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
#chat-input textarea:focus {
    border-color: rgba(120,80,220,0.5) !important;
    box-shadow: 0 0 20px rgba(120,80,220,0.15) !important;
    outline: none !important;
}
#chat-input textarea::placeholder {
    color: rgba(255,255,255,0.2) !important;
}

/* ===== 按钮通用样式 ===== */
button, .gr-button {
    transition: all 0.3s ease !important;
    border-radius: 10px !important;
    letter-spacing: 0.5px !important;
}
.gr-button-primary {
    background: linear-gradient(135deg, #7b2ff7, #4f46e5) !important;
    border: none !important;
    box-shadow: 0 4px 16px rgba(123,47,247,0.35) !important;
    font-weight: 600 !important;
}
.gr-button-primary:hover {
    box-shadow: 0 6px 24px rgba(123,47,247,0.5) !important;
    transform: translateY(-1px);
}
.gr-button-primary:active {
    transform: translateY(1px);
    box-shadow: 0 2px 8px rgba(123,47,247,0.3) !important;
}
.gr-button-secondary {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94a3b8 !important;
}
.gr-button-secondary:hover {
    background: rgba(255,255,255,0.1) !important;
    border-color: rgba(255,255,255,0.2) !important;
}

/* 生成按钮 loading 动画 */
.gr-button-primary:disabled,
.gr-button-primary[disabled] {
    background: linear-gradient(135deg, #4a1d8a, #312e81) !important;
    opacity: 0.7 !important;
    cursor: not-allowed !important;
}

/* ===== 下拉框 & 输入框 ===== */
.gr-dropdown, .gr-textbox {
    border-radius: 10px !important;
}
.gr-dropdown label, .gr-textbox label {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* ===== Gallery 缩略图 ===== */
.gr-gallery {
    border-radius: 12px !important;
    background: rgba(0,0,0,0.2) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
}

/* ===== 隐藏 footer ===== */
footer { display: none !important; }

/* ===== Markdown 文本 ===== */
.prose {
    color: #cbd5e1 !important;
}

/* ===== 面板内部间距 ===== */
.main-row > div {
    display: flex !important;
    flex-direction: column !important;
}
.preview-panel > * + * { margin-top: 14px !important; }
.sidebar-panel > * + * { margin-top: 10px !important; }
.chat-panel > * + * { margin-top: 10px !important; }

/* ===== 全局平滑过渡 ===== */
.gradio-container * {
    transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, opacity 0.3s ease;
}
"""

NO_PREVIEW = "🎨 素材将在此处实时预览\n\n*在左侧输入描述后点击「生成」开始创作*"

WELCOME_CHAT = [
    {
        "role": "assistant",
        "content": (
            "### 👋 你好！我是 2D 游戏素材 AI 生成助手\n\n"
            "我可以帮你生成各种 **2D 游戏素材**，包括角色、道具、场景、UI、特效等。\n\n"
            "**🚀 快速开始：**\n"
            "- 在下方输入框中描述你想要的素材\n"
            "- 点击 ✨ 生成 按钮或按 Enter 键\n"
            "- 生成结果会在右侧实时预览\n\n"
            "**💡 提示：** 也可以用顶部快捷按钮一键填充示例描述！"
        ),
    }
]


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
        return None, f"⚠️ 图片下载失败，请重试", None
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
        WELCOME_CHAT.copy(),
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
                    ex_btn1 = gr.Button("⚔️ 战士", size="sm")
                    ex_btn2 = gr.Button("🧪 药水", size="sm")
                    ex_btn3 = gr.Button("🌲 场景", size="sm")
                    ex_btn4 = gr.Button("🪙 金币", size="sm")
                    ex_btn5 = gr.Button("💀 Boss", size="sm")
                    rand_btn = gr.Button("🎲 随机", size="sm")
            with gr.Column(scale=1):
                status_md = gr.Markdown("当前：**像素风** · **通用**")
                clear_btn = gr.Button("🗑️ 清空对话", variant="secondary", size="sm")

        with gr.Row(elem_classes="main-row"):
            with gr.Column(scale=5, elem_classes="chat-panel"):
                chatbot = gr.Chatbot(
                    label="💬 对话",
                    value=WELCOME_CHAT,
                    height=560,
                    buttons=["copy"],
                    show_label=True,
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="描述你的素材，例如：持盾的骑士角色，蓝色盔甲，待机姿势…",
                        label="素材描述",
                        scale=6,
                        lines=2,
                        elem_id="chat-input",
                    )
                    send_btn = gr.Button("✨ 生成", variant="primary", scale=1)

            with gr.Column(scale=3, elem_classes="preview-panel"):
                gr.Markdown("### 🖼️ 素材在线预览")
                preview = gr.Image(
                    label="",
                    height=400,
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
                    height=160,
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

        gen_outputs_no_btn = [chatbot, msg_input, preview, preview_info, save_btn, gallery]
        gen_outputs = gen_outputs_no_btn + [send_btn]

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
        primary_hue="violet",
        secondary_hue="blue",
        neutral_hue="slate",
    ).set(
        body_background_fill="#06060c",
        body_background_fill_dark="#06060c",
        block_background_fill="rgba(255,255,255,0.03)",
        block_background_fill_dark="rgba(255,255,255,0.03)",
        block_border_color="rgba(255,255,255,0.06)",
        block_label_text_color="#a5b4fc",
        input_background_fill="rgba(255,255,255,0.04)",
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
