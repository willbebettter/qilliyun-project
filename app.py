"""Gradio Web 可视化界面"""

import random
import re
import shutil
from pathlib import Path

import gradio as gr

from core import (
    CATEGORY_TEMPLATES,
    EXAMPLE_PROMPTS,
    OUTPUT_DIR,
    RANDOM_PROMPTS,
    STYLE_PRESETS,
    chat,
    clear_current_session_dir,
    create_executor,
)

_CSS_PATH = Path(__file__).parent / "style.css"

NO_PREVIEW = "🎨 素材将在此处实时预览\n\n*在左侧输入描述后点击「生成」开始创作*"


class Session:
    def __init__(self):
        self.style = "像素风"
        self.category = ""
        self.executor = None
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
    if not p.is_file():
        return NO_PREVIEW
    size_kb = p.stat().st_size // 1024
    return (
        f"**{p.name}**  \n"
        f"尺寸 1024×1024 · {size_kb} KB  \n"
        f"描述：{prompt or '—'}  \n"
        f"💡 点击图片中央可全屏查看（按 Esc 退出）"
    )


def _build_final_prompt(user_prompt: str, style: str, category: str) -> str:
    style_hint = STYLE_PRESETS.get(style, "")
    cat_template = CATEGORY_TEMPLATES.get(category, "")
    if category and cat_template:
        base = cat_template.format(desc=user_prompt.strip())
    else:
        base = user_prompt.strip()
    if not base.endswith("。"):
        base = base.rstrip(".,。") + "，"
    if style_hint:
        base = base + f"风格要求：{style_hint}。"
    return base


def _save_with_dialog(source_path: str | None) -> str:
    """弹出系统文件保存对话框，让用户选择保存位置。"""
    if not source_path or not Path(source_path).is_file():
        return "⚠️ 没有可保存的图片"

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        src_name = Path(source_path).name
        initial_file = src_name if src_name else "素材.png"

        save_path = filedialog.asksaveasfilename(
            title="保存素材图片",
            initialfile=initial_file,
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg"),
                ("WebP 图片", "*.webp"),
                ("所有文件", "*.*"),
            ],
        )
        root.destroy()

        if not save_path:
            return "已取消保存"

        shutil.copy2(source_path, save_path)
        return f"✅ 已保存到：{save_path}"

    except Exception as e:
        try:
            dest_dir = Path.home() / "Desktop"
            dest = dest_dir / Path(source_path).name
            shutil.copy2(source_path, str(dest))
            return f"✅ 已保存到桌面：{dest.name}\n\n（文件保存对话框不可用，已自动保存到桌面）"
        except Exception:
            return f"⚠️ 保存失败：{str(e)}"


def respond_generator(message, history):
    if not message.strip():
        yield history, "", None, NO_PREVIEW, gr.update(interactive=False), gr.update(interactive=False)
        return

    final_prompt = _build_final_prompt(message, session.style, session.category)
    category_display = session.category or "通用"

    loading_history = history + [
        {"role": "user", "content": message},
        {
            "role": "assistant",
            "content": "🎨 **AI 正在生成素材中…**  \n\n"
            f"🎨 风格：**{session.style}**  ·  📂 分类：**{category_display}**\n"
            f"（融合提示词：{final_prompt[:80]}{'…' if len(final_prompt) > 80 else ''}）\n\n"
            '<span class="loading-dots"><span></span><span></span><span></span></span>'
        },
    ]
    yield (
        loading_history,
        "",
        None,
        NO_PREVIEW,
        gr.update(interactive=False),
        gr.update(interactive=False),
    )

    try:
        session.ensure_executor()
        reply, local_path, remote_url = chat(session.executor, final_prompt)

        if local_path and Path(local_path).is_file():
            session.current_image = local_path
            preview_path = local_path
            info = _preview_info(local_path, message)
            url_display = remote_url if remote_url else "（本地已保存）"
            display_reply = reply + f"\n\n🖼️ 图片链接：{url_display}\n\n✅ 素材已生成，请在右侧预览窗口查看"
        elif remote_url:
            session.current_image = None
            preview_path = None
            info = (
                f"⚠️ 图片下载到本地失败\n\n"
                f"远程图片链接：{remote_url}\n\n"
                f"请尝试复制链接在浏览器中打开查看"
            )
            display_reply = reply + f"\n\n🖼️ 图片链接：{remote_url}\n\n⚠️ 图片下载失败，请点击链接在浏览器查看"
        else:
            session.current_image = None
            preview_path = None
            info = NO_PREVIEW
            display_reply = reply

        final_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": display_reply},
        ]
        has_image = session.current_image is not None

        yield (
            final_history,
            "",
            preview_path,
            info,
            gr.update(interactive=has_image),
            gr.update(interactive=False),
        )

    except Exception as e:
        error_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": f"❌ 生成异常：{str(e)}\n\n请检查网络或 API 配置后重试"},
        ]
        yield (
            error_history,
            "",
            None,
            NO_PREVIEW,
            gr.update(interactive=False),
            gr.update(interactive=False),
        )


def _toggle_send_btn(text: str):
    has_content = bool(text and text.strip())
    return gr.update(interactive=has_content)


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
    clear_current_session_dir()
    session.reset_executor()
    session.current_image = None
    return (
        [],
        "",
        None,
        NO_PREVIEW,
        gr.update(interactive=False),
        "🔄 已新建对话",
    )


def quick_generate(prompt_text: str, history):
    if not prompt_text.strip():
        yield history, "", None, NO_PREVIEW, gr.update(interactive=False), gr.update(interactive=True)
        return
    yield from respond_generator(prompt_text, history)


def random_example():
    return random.choice(RANDOM_PROMPTS)


def build_ui():
    with gr.Blocks(title="PixelForge - 2D游戏素材AI生成器") as demo:

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

        gr.HTML("""
<div id="image-fullscreen-overlay" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh;
  background:rgba(0,0,0,0.92); z-index:99999; cursor:pointer;
  display:none; align-items:center; justify-content:center;"
  onclick="this.style.display='none'">
  <img id="image-fullscreen-img" style="max-width:95vw; max-height:95vh; object-fit:contain;
    border-radius:12px; box-shadow:0 0 80px rgba(139,92,246,0.3);" />
  <span style="position:absolute; top:24px; right:36px; color:#fff; font-size:32px;
    opacity:0.6; cursor:pointer;" onclick="document.getElementById('image-fullscreen-overlay').style.display='none'">&times;</span>
</div>
<script>
(function() {
  function setupImageClick() {
    var previewImg = document.querySelector('#preview-window img');
    if (!previewImg) return;
    if (previewImg.dataset.clickSetup === '1') return;
    previewImg.dataset.clickSetup = '1';
    previewImg.style.cursor = 'pointer';
    previewImg.addEventListener('click', function(e) {
      var overlay = document.getElementById('image-fullscreen-overlay');
      var fullImg = document.getElementById('image-fullscreen-img');
      fullImg.src = previewImg.src;
      overlay.style.display = 'flex';
      e.stopPropagation();
    });
  }
  setInterval(setupImageClick, 800);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.getElementById('image-fullscreen-overlay').style.display = 'none';
    }
  });
})();
</script>
""")

        gr.Markdown("# 🎮 PixelForge", elem_id="main-title")
        gr.Markdown(
            "Powered by Qwen + Wanx · 生成后可在右侧实时预览，并保存到本地",
            elem_id="subtitle",
        )

        with gr.Row(elem_classes="settings-row"):
            with gr.Column(scale=1):
                gr.Markdown("⚙️ **风格设置**", elem_classes="section-label")
                style_dd = gr.Dropdown(
                    choices=[f" {k}" for k in STYLE_PRESETS.keys()],
                    value=" 像素风",
                    label="🎨 画风",
                    allow_custom_value=False,
                    filterable=False,
                )
            with gr.Column(scale=1):
                gr.Markdown("📂 **素材分类**", elem_classes="section-label")
                cat_dd = gr.Dropdown(
                    choices=[" （通用）"] + [f" {k}" for k in CATEGORY_TEMPLATES.keys()],
                    value=" （通用）",
                    label="📦 素材分类",
                    allow_custom_value=False,
                    filterable=False,
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

        with gr.Row(elem_classes="main-row"):
            with gr.Column(scale=5, elem_classes="chat-panel"):
                gr.Markdown("### 💬 对话区")
                chatbot = gr.Chatbot(
                    value=[],
                    placeholder="输入素材描述，点击 ✨ 生成 开始创作你的2D游戏素材",
                    height=600,
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
                gr.Markdown("### 🖼️ 素材在线预览")
                preview = gr.Image(
                    height=400,
                    show_label=False,
                    show_download_button=False,
                    show_fullscreen_button=False,
                    interactive=False,
                    elem_id="preview-window",
                )
                preview_info = gr.Markdown(
                    NO_PREVIEW,
                    elem_id="preview-info-area",
                )

                gr.Markdown("### 💾 保存到本地")
                save_btn = gr.Button(
                    "💾 保存到本地（选择位置）",
                    variant="primary",
                    interactive=False,
                    size="lg",
                )
                save_status = gr.Markdown(
                    "生成素材后点击按钮，选择保存位置"
                )

                gr.Markdown("### 📌 使用提示")
                gr.Markdown(
                    """
- **风格设置**：选择不同的画风风格，影响生成效果
- **素材分类**：选择素材类型（角色/道具/场景等）
- **快捷生成**：点击顶部按钮一键生成示例素材
- **图片存储**：本轮对话图片自动保存到 `output/current_session_images/` 文件夹
- **保存到本地**：点击按钮弹出系统文件对话框，可选择保存位置
                    """,
                    elem_classes="tips-area",
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

        msg_input.change(_toggle_send_btn, [msg_input], [send_btn])

        gen_outputs = [chatbot, msg_input, preview, preview_info, save_btn, send_btn]

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
            lambda: _save_with_dialog(session.current_image),
            outputs=[save_status],
        )

        new_btn.click(
            new_conversation,
            outputs=[chatbot, msg_input, preview, preview_info, save_btn, status_md],
        )

        qg_outputs = [chatbot, msg_input, preview, preview_info, save_btn, send_btn]

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
        clear_current_session_dir()
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