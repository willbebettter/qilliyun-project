from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_classic.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import SecretStr
from langchain_core.tools import tool
import warnings
import dashscope
from http import HTTPStatus
warnings.filterwarnings("ignore", category=DeprecationWarning)
@tool
def generate_image(prompt1: str) -> str:
    """根据文字描述生成图片，返回2D游戏素材主题的像素风的图片的URL。当用户需要生成图片、画图、创作图像时使用此工具。"""
    dashscope.api_key = "sk-4d5c7fc8527242d1b578fdb48baee2a0"
    rsp = dashscope.ImageSynthesis.call(
        model="wanx-v1",
        prompt=prompt1+"(注意:要符合2D游戏风格,不需要图片多精美但必须契合,尤其是符合2D游戏风格)",
        n=1,
        size="1024*1024",
    )
    if rsp.status_code == HTTPStatus.OK:
        return rsp.output.results[0].url
    else:
        return f"图片生成失败,返回错误信息: {rsp.message}"
llm = ChatOpenAI(
    model="qwen-turbo", # 改用文本模型
    temperature=0.3,
    api_key=SecretStr("sk-4d5c7fc8527242d1b578fdb48baee2a0"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
tools = [generate_image]
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个拥有高效生图的强力工具的ai,需根据用户需求高效的匹配生成对应的2D游戏素材的图片,不要求质量很高但必须十分契合2D游戏主题,且必需返回信息给用户不能不返回哪怕报错也得返回"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, memory=ConversationBufferMemory(memory_key="chat_history",return_messages=True))
print("-----------本地搭建langchaind调用生成素材图片agent智能体------------")
while True:
    question = input("请输入需求或问题(输入`exit`或`结束`即可退出): ")
    if question == "exit"or question == "退出":
        exit()
    print(executor.invoke({"input": question}).content)