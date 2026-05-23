# 游戏2D素材生成

基于 LangChain 和阿里云 DashScope 构建的 AI Agent，可根据文字描述生成 2D 游戏风格素材图。

## 功能特性

- **Web 可视化界面**：Gradio 驱动，右侧大图在线预览 + 历史画廊
- **保存到本地**：一键下载，支持自定义文件名另存
- **Rich 终端模式**：彩色面板、加载动画、风格/分类切换
- **6 种画风预设**：像素风、卡通、等距视角、手绘、暗黑奇幻、赛博朋克
- **6 类素材模板**：角色、道具、场景、UI元素、怪物、特效
- **对话记忆**：多轮对话，Agent 记住上下文
- **快捷示例**：一键填充常用提示词

## 技术栈

- **框架**：LangChain (Agents + Memory)
- **语言模型**：Qwen Turbo (阿里云 DashScope)
- **图像模型**：Wanx v1 (阿里云 DashScope)
- **Web UI**：Gradio 4
- **终端 UI**：Rich

## 项目结构

```
游戏2D素材生成/
├── agent-ok.py       # 主入口（默认 Web，--cli 终端模式）
├── app.py            # Gradio Web 界面
├── cli.py            # Rich 终端界面
├── core.py           # Agent 核心逻辑
├── requirements.txt  # 依赖
├── .env.example      # API Key 配置示例
└── Readme.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 DashScope API Key：

```bash
copy .env.example .env
```

或在终端设置环境变量：

```bash
set DASHSCOPE_API_KEY=your_key_here
```

### 3. 启动

**Web 界面（推荐）：**

```bash
python agent-ok.py
```

浏览器会自动打开 `http://127.0.0.1:7860`

**终端模式：**

```bash
python agent-ok.py --cli
```

终端内置命令：`help` · `style` · `cat` · `random` · `clear` · `exit`

## 使用示例

在 Web 界面或终端中输入：

```
持剑的精灵战士，绿色盔甲，待机姿势
```

选择「像素风」+「角色」分类，即可生成契合 2D 游戏的素材图。

## 注意事项

- 需要有效的阿里云 DashScope API Key
- 生成的图片为 1024×1024 像素
- API Key 请勿提交到版本控制
