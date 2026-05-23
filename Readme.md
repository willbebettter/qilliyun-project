# 游戏2D素材生成

基于 LangChain 和阿里云 DashScope 构建的 AI Agent，可根据文字描述生成 2D 游戏风格素材图。

## 功能特性

- **AI 智能生图**：通过自然语言描述，自动生成契合 2D 游戏风格的像素风素材
- **对话记忆**：支持多轮对话，Agent 会记住之前的交互上下文
- **交互式界面**：命令行实时交互，输入需求即可获得素材图片

## 技术栈

- **框架**：LangChain (Agents + Memory)
- **语言模型**：Qwen Turbo (阿里云 DashScope)
- **图像模型**：Wanx v1 (阿里云 DashScope)
- **API**：阿里云 DashScope

## 项目结构

```
游戏2D素材生成/
├── agent-ok.py      # 主程序入口
└── README.md        # 项目说明文档
```

## 依赖安装

```bash
pip install langchain langchain-openai langchain-classic dashscope pydantic
```

## 使用方法

1. 确保环境变量或代码中配置了有效的阿里云 DashScope API Key
2. 运行程序：
   ```bash
   python agent-ok.py
   ```
3. 在交互式提示符下输入图片需求描述
4. 输入 `exit` 或 `退出` 结束程序

## 示例

```
请输入需求或问题(输入`exit`或`结束`即可退出): 生成一只拿着剑的战士角色
(返回2D游戏风格的战士素材图片URL)
```

## 注意事项

- 需要有效的阿里云 DashScope API Key
- 生成的图片为 1024x1024 像素
- 图片风格自动适配 2D 游戏主题
