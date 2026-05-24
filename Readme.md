# 🎮 2D 游戏素材 AI 生成器

基于 LangChain Agent + 阿里云 DashScope 构建的 AI 驱动 2D 游戏素材生成工具。输入文字描述，自动生成像素风、卡通、赛博朋克等多种风格的 2D 游戏素材图。

## ✨ 功能特性

- **Web 可视化界面**：暗黑极光主题，左侧对话 + 右侧实时预览
- **智能对话判断**：AI 自动区分「图片生成请求」和「普通对话」，非生图请求不会触发工具调用
- **6 种画风预设**：像素风、卡通、等距视角、手绘、暗黑奇幻、赛博朋克
- **6 类素材模板**：角色、道具、场景、UI元素、怪物、特效
- **提示词融合**：画风 + 分类设置自动与用户描述融合，提升生成质量
- **90+ 精细提示词模板**：一键随机生成，每个模板包含详细视觉描述
- **即时下载**：图片生成后立即下载到本地，避免签名过期
- **系统文件对话框**：保存时弹出原生文件选择器，用户自选存储位置
- **会话图片管理**：每轮对话图片独立存储，新对话自动清理
- **终端模式**：支持 Rich 彩色终端交互（`--cli`）

## 🛠 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | LangChain (Agents + Memory + Tools) |
| 语言模型 | Qwen Turbo (阿里云 DashScope) |
| 图像模型 | Wanx v1 (阿里云 DashScope) |
| Web UI | Gradio 4 |
| 终端 UI | Rich |

## 📁 项目结构

```
游戏2D素材生成/
├── agent-ok.py       # 主入口（默认 Web，--cli 终端模式）
├── app.py            # Gradio Web 界面
├── cli.py            # Rich 终端界面
├── core.py           # Agent 核心逻辑（LLM + 工具 + 下载）
├── style.css         # 暗黑极光主题样式
├── requirements.txt  # Python 依赖
├── .env.example      # API Key 配置模板
├── .gitignore
└── Readme.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 DashScope API Key：

```bash
copy .env.example .env
```

编辑 `.env` 文件：
```
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

> API Key 获取：[阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)

或在终端设置环境变量：

```bash
# Windows
set DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# Linux/macOS
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3. 启动

**Web 界面（推荐）：**

```bash
python agent-ok.py
```

浏览器自动打开 `http://127.0.0.1:7860`

**终端模式：**

```bash
python agent-ok.py --cli
```

终端内置命令：`help` · `style` · `cat` · `random` · `clear` · `exit`

## 📖 使用说明

### Web 界面

1. **顶部设置区**：选择画风和素材分类，点击快捷按钮一键生成
2. **左侧对话区**：输入素材描述，AI 自动判断是否需要生图
   - 输入「生成一个战士角色」→ 调用生图工具
   - 输入「你好」或「什么是像素风」→ 纯文字对话
3. **右侧预览区**：实时预览生成的素材图片
4. **保存到本地**：点击按钮弹出系统文件对话框，选择保存位置

### 画风说明

| 画风 | 效果描述 |
|------|---------|
| 像素风 | 16-bit 复古像素风格，清晰像素点 |
| 卡通 | 可爱卡通风格，粗描边，鲜艳色彩 |
| 等距视角 | 等距2D俯视对角线视角 |
| 手绘 | 手绘素描风格，有机线条，水彩质感 |
| 暗黑奇幻 | 暗黑RPG风格，阴郁光照，哥特元素 |
| 赛博朋克 | 赛博朋克霓虹风格，未来UI元素，发光点缀 |

### 素材分类说明

| 分类 | 自动追加的提示词 |
|------|----------------|
| 角色 | 2D game character sprite, full body, transparent background |
| 道具 | 2D game item icon, centered, transparent background |
| 场景 | 2D game background scene, wide composition |
| UI元素 | 2D game UI element, clean design |
| 怪物 | 2D game enemy sprite, full body, transparent background |
| 特效 | 2D game visual effect, particle style |

### 图片存储

- 生成的图片自动保存到 `output/current_session_images/` 文件夹
- 新建对话时自动清理上一轮图片
- 点击「保存到本地」按钮可选择自定义位置另存

## ⚠️ 注意事项

- 需要有效的阿里云 DashScope API Key
- 生成的图片为 1024×1024 像素
- 图片 URL 为临时签名链接，有时效性（程序已做即时下载处理）
- API Key 请勿提交到版本控制
- 建议使用 Python 3.10+

## 📄 依赖列表

```
langchain
langchain-openai
langchain-classic
dashscope
pydantic
python-dotenv
rich
gradio>=4.0
```
