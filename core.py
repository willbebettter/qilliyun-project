"""2D 游戏素材生成 Agent 核心模块"""

import os
import re
import time
import warnings
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import dashscope
import requests
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

RANDOM_PROMPTS = [
    "持剑的精灵战士角色，翠绿色叶纹盔甲，尖耳银发，手持发光的精灵长剑，待机站立姿势，透明背景",
    "红色治疗药水图标，心形玻璃瓶装，瓶内红色发光液体带气泡上升，瓶口软木塞，透明背景居中",
    "森林关卡横版卷轴背景，三层视差构图，前景灌木草丛，中景粗壮大树，远景朦胧山脉，晨光穿透树叶",
    "金币UI图标，圆形金币堆叠，正面刻有皇冠浮雕，金色光泽高光，深色底板衬托，居中构图",
    "火焰骷髅Boss全身立绘，紫色火焰环绕骨架，头骨眼窝燃烧红光，手持骨剑，暗红斗篷残片飘动，透明背景",
    "魔法爆炸特效，蓝色魔法能量从中心向四周扩散，粒子碎片飞溅，中心白色高光，外圈蓝色渐变消散",
    "冰霜巨龙Boss全身立绘，冰蓝色龙鳞铠甲，巨翼展开吐出寒气，脚下冰晶凝结，暗蓝背光，透明背景",
    "暗影刺客角色全身立绘，黑色破烂斗篷遮面，双持暗金匕首，红色眼瞳微光，身形半隐于暗影，透明背景",
    "治疗药水道具图标，绿色玻璃瓶装，瓶内翠绿液体带金色光点气泡，瓶身刻有十字纹，软木塞封口，透明背景",
    "魔法卷轴道具图标，泛黄羊皮纸卷轴，展开状态，金色符文悬浮飘出，两端红色封印绳，透明背景居中",
    "城堡大厅场景背景，哥特式石柱拱门排列，两侧墙壁火炬照明，红地毯延伸至王座，穹顶彩绘玻璃",
    "技能冷却UI图标，沙漏造型，蓝色流沙从上向下流动，外框银色金属质感，半透明底板，居中构图",
    "巨型蜘蛛怪物全身立绘，紫色斑纹覆盖八条节肢，八只红色复眼，腹部毒腺鼓胀，蛛丝垂挂，透明背景",
    "雷电术施法特效，从指尖释放金色闪电链，电弧分叉跳跃，紫色雷云背景，地面电弧扩散，中心高光",
    "狂战士角色全身立绘，赤裸上身肌肉隆起，双手高举锈蚀巨斧，面部狂暴表情，红色战纹涂装，透明背景",
    "法力药水道具图标，蓝紫色琉璃瓶装，瓶内漩涡状液体发光，钻石形瓶塞，瓶身刻有星辰纹，透明背景",
    "地下城洞穴场景背景，钟乳石倒挂，地下暗河倒影，岩壁苔藓，角落骷髅残骸，幽蓝火把照明，潮湿雾气",
    "生命值UI血条图标，红宝石质感长条形，金色边框雕花，内部红色液体波动，左侧心形图标，居中构图",
    "暗黑武士Boss全身立绘，全覆式黑色重甲，手持暗红长刀，红色斗气从铠甲缝隙溢出，头盔T形眼缝红光，透明背景",
    "火焰箭矢飞行特效，箭头燃烧橙色火焰，拖尾红黄粒子渐变消散，飞行轨迹弧线，暗色背景衬托",
    "精灵弓箭手角色全身立绘，绿色斗篷兜帽，长弓满拉姿态，箭矢搭弦待发，尖耳金发，森林背景虚化，透明背景",
    "护盾药水道具图标，金色光泽菱形瓶装，瓶内金色液体带盾牌形沉淀物，瓶塞镶嵌蓝宝石，透明背景居中",
    "沙漠废墟场景背景，金字塔残垣断壁，风沙弥漫，枯萎棕榈树，沙丘起伏，落日余晖橙红天空",
    "经验值UI进度条图标，蓝色水晶质感长条，内部星光流动，金色刻度标记，左侧星形图标，居中构图",
    "机械傀儡Boss全身立绘，黄铜齿轮关节，蒸汽从肩部喷涌，独眼红色透镜，铁链缠绕手臂，锈蚀金属外壳，透明背景",
    "冰霜新星施法特效，白色冰晶从中心爆裂扩散，六角形冰棱向外延伸，蓝色寒气雾化，地面结冰纹理",
    "圣骑士角色全身立绘，银白色全身板甲，金色圣光从铠甲缝隙溢出，手持十字圣盾，白色披风飘扬，透明背景",
    "宝石道具图标，六边形切割紫水晶，七彩折射光斑，银色镶座托底，深色绒布衬底，居中构图",
    "雪山之巅场景背景，暴风雪肆虐，冰晶飘飞，险峻岩峰，远处雪山连绵，灰白天空乌云压顶",
    "背包UI格图标，棕色皮革纹理方格，金属铆钉四角，翻盖扣带，内衬深色布料，居中构图",
    "地狱三头犬Boss全身立绘，三个犬头各自咆哮，锁链项圈束缚，熔岩皮肤裂缝溢出岩浆，尾巴是蛇，透明背景",
    "神圣治愈施法特效，金色光芒从天而降，十字形光柱笼罩，白色羽毛飘落，地面金色法阵，温暖光晕",
    "忍者角色全身立绘，深蓝夜行衣蒙面，腰间手里剑带，右手持苦无，左手结印，身姿半蹲警戒，透明背景",
    "钥匙道具图标，古铜色长柄钥匙，齿纹精致复杂，柄端龙形雕花，金属光泽高光，深色底板衬托，居中构图",
    "海盗船甲板场景背景，木质甲板铺板，桅杆帆布飘动，船舷海浪拍打，加农炮排列，远处海平线夕阳",
    "技能树UI节点图标，星芒形节点，金色连线延伸，中心宝石发光，外圈小节点排列，深色底板，居中构图",
    "石像鬼怪物全身立绘，灰色花岗岩质感皮肤，蝙蝠翅膀展开，尖角兽面，蹲踞姿态蓄力，苔藓覆盖肩部，透明背景",
    "旋风斩攻击特效，青色剑气形成旋转风暴，中心人物剪影，外围碎片飞溅，地面尘土扬起，动态模糊",
    "德鲁伊角色全身立绘，鹿角头饰缠绕藤蔓，褐色皮甲，手持曲木法杖顶端发光宝石，肩停猫头鹰，透明背景",
    "宝箱道具图标，木质宝箱打开状态，金色镶边铆钉，内部金币珠宝溢出，白色光芒从箱内射出，居中构图",
    "浮游岛场景背景，悬浮岩石岛屿，瀑布从边缘倾泻入云海，古树盘根，云层环绕，远处飞鸟剪影",
    "聊天框UI图标，半透明深色底板，圆角矩形气泡，左侧玩家头像占位，底部输入框，羽化边缘，居中构图",
    "深海巨兽Boss全身立绘，巨型章鱼形态，八条触手挥舞，吸盘密布，生物荧光蓝色斑点，深海暗蓝背光，透明背景",
    "传送门特效，紫色漩涡光效，中心裂隙扭曲空间，边缘电弧闪烁，地面碎石悬浮，暗紫色调弥漫",
    "熊猫武僧角色全身立绘，黑白熊猫人，中式布衣束腰，手持竹棍架势，腰间葫芦，竹林背景虚化，透明背景",
    "盾牌道具图标，鸢盾造型，银色盾面刻有狮鹫徽章，蓝色珐琅底色，盾沿金色包边，战损划痕，居中构图",
    "霓虹街道场景背景，赛博朋克风格，全息广告牌闪烁，雨后湿滑路面倒影，高楼LED屏幕，紫粉霓虹灯光",
    "小地图UI图标，圆形裁切地图，绿色地形标注，红色指南针标记，半透明底板，边框金属质感，居中构图",
    "吸血鬼伯爵Boss全身立绘，苍白面容红眼尖牙，黑色燕尾服高领披风，手持红酒杯，蝙蝠群环绕，暗红月光，透明背景",
    "毒雾领域施法特效，绿色瘴气从地面升腾扩散，气泡破裂释放毒雾，中心紫色毒核，枯萎植物轮廓，腐蚀纹理",
    "小魔女角色全身立绘，紫色尖帽星辰装饰，骑扫帚飞行姿态，脚下星月法阵发光，手持魔杖，黑猫伴飞，透明背景",
    "魔法书道具图标，厚重的皮革封面，金色锁扣，翻开状态，符文从书页飘出发光，书脊宝石镶嵌，居中构图",
    "樱花庭院场景背景，日式木桥横跨池塘，樱花树花瓣飘落，石灯笼排列，锦鲤游动，远山薄雾，柔和粉色调",
    "对话框UI图标，圆角气泡形状，左侧角色头像框，底部文字行占位，尾部三角箭头，半透明底板，居中构图",
    "岩石巨人Boss全身立绘，巨大人形岩石躯体，青苔藤蔓覆盖全身，背部水晶矿脉发光，双眼琥珀色，碎石坠落，透明背景",
    "陨石坠落特效，巨大燃烧陨石从天空坠落，橙红火焰尾迹，地面冲击波扩散，碎石飞溅，暗红天空裂痕",
    "海盗船长角色全身立绘，三角帽骷髅标志，红色长衣金扣，左手弯刀右手铁钩，独眼罩，肩停鹦鹉，透明背景",
    "藏宝图道具图标，泛黄羊皮纸展开，红色X标记，虚线路径，边缘烧焦，指南针玫瑰图案，居中构图",
    "太空站场景背景，科幻风格空间站内部，金属走廊，星光舷窗外星云，全息投影面板，蓝色应急灯光",
    "任务面板UI图标，羊皮纸底纹卷轴，左侧羽毛笔图标，任务文字行占位，金色边框，完成勾选标记，居中构图",
    "九尾妖狐Boss全身立绘，九条火焰尾巴展开，魅惑紫色瞳孔，人形狐耳白衣，樱花花瓣环绕，赤足悬浮，透明背景",
    "圣光护盾防御特效，金色六边形蜂巢光墙，中心十字圣徽，光粒子从边缘飘散，半透明屏障，温暖金色调",
    "机甲战士角色全身立绘，银灰合金装甲，胸口红光反应堆，背部喷射背包喷出蓝色火焰，手持能量步枪，透明背景",
    "齿轮道具图标，黄铜材质咬合齿轮组，蒸汽朋克风格，中心主齿轮带动小齿轮，金属光泽高光，居中构图",
    "蘑菇森林场景背景，巨大菌伞遮天，荧光孢子飘浮，地面苔藓蘑菇丛，小径蜿蜒，紫绿荧光色调，梦幻氛围",
    "成就徽章UI图标，圆形金属徽章，浮雕图案，红缎带垂挂，金色边缘锯齿，中心宝石，深色绒布底板，居中构图",
    "深渊恶魔Boss全身立绘，巨大人形暗红皮肤，黑色羽翼展开，头顶弯角，熔岩裂隙覆盖全身，手持三叉戟，透明背景",
    "水龙卷施法特效，蓝色水纹从地面旋转上升形成龙卷，水花飞溅，中心深蓝漩涡，外围水雾弥漫，动态扭曲",
    "狼人角色全身立绘，银灰浓密毛发覆盖，肌肉隆起，利爪伸出，满月光辉照耀，仰天嚎叫姿态，透明背景",
    "望远镜道具图标，黄铜伸缩筒三节，皮革包裹握把，前端大镜头反光，系绳悬挂，金属光泽，居中构图",
    "水墨竹林场景背景，中国风水墨画风格，飞白笔触竹林，留白云雾，小径石阶，远处凉亭，墨色浓淡层次",
    "排行榜UI图标，水晶底座金色冠冕，三根立柱高低排列，数字占位，星光粒子装饰，半透明底板，居中构图",
    "美杜莎Boss全身立绘，蛇发缠绕扭动，石化凝视绿色眼光，苍白面容，蛇尾下身盘踞，手持铜镜，石质纹理蔓延，透明背景",
    "光之翼飞行特效，白色羽毛从翅膀飘落散开，金色光粒子轨迹，柔和光晕笼罩，翅膀剪影，圣洁白金色调",
    "哥布林商人角色全身立绘，矮小绿色皮肤，大背包塞满杂物，腰间金币袋叮当，狡黠笑容，手持算盘，透明背景",
    "灯笼道具图标，中式宫灯红木框架，红色丝绸灯罩，柔和暖黄光晕，金色流苏垂挂，顶部挂钩，居中构图",
    "火山地狱场景背景，岩浆从火山口喷发，黑烟滚滚，熔岩河流，焦黑岩石，暗红天空闪电，末日氛围",
    "好友列表UI图标，竖排列表布局，圆形头像占位框，在线绿点亮起，好友名称行，半透明底板，居中构图",
    "克苏鲁触手Boss全身立绘，粘液质感深绿皮肤，无数触手从暗处伸出，眼球密布触手末端，巨口裂开，暗紫背光，透明背景",
    "樱花散落环境特效，粉色花瓣从上方飘飞散落，花瓣旋转翻飞，地面花瓣堆积，微风轨迹线，柔和粉白色调",
    "大天使角色全身立绘，六翼白色光羽展开，金色铠甲胸甲，手持审判之剑发光，光环笼罩头顶，白金色调，透明背景",
    "闪电链攻击特效，白色电光从中心跳跃分叉，击中多个目标剪影，紫色雷云背景，地面焦痕，电弧残影",
    "魔法水晶矿道具图标，紫色晶体簇从岩壁生长，底部发光底座，内部星光流动，周围碎晶散落，深色底板衬托，居中构图",
    "沼泽湿地场景背景，枯树歪斜，浓密雾气弥漫，萤火虫点点绿光，水面倒影，腐殖质地面，阴森绿色调",
    "毒液史莱姆怪物全身立绘，绿色半透明凝胶体，内部骨骼残骸可见，分裂增殖小体，粘液滴落，气泡鼓动，透明背景",
    "施法吟唱特效，地面符文法阵旋转扩散，金色光纹从圆环升起，中心施法者剪影，能量汇聚光柱，魔法粒子环绕",
]

OUTPUT_DIR = Path(__file__).parent / "output"
CURRENT_SESSION_DIR = OUTPUT_DIR / "current_session_images"

_last_result = {
    "local_path": None,
    "remote_url": None,
}


def get_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "未找到 DASHSCOPE_API_KEY，请设置环境变量或在项目根目录创建 .env 文件：\n"
            "  DASHSCOPE_API_KEY=your_key_here"
        )
    return key


def clear_current_session_dir() -> None:
    try:
        if CURRENT_SESSION_DIR.exists():
            for f in CURRENT_SESSION_DIR.glob("*.png"):
                f.unlink(missing_ok=True)
        CURRENT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _safe_filename(text: str, max_len: int = 24) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return (cleaned or "asset")[:max_len]


def _immediate_download(url: str, prompt: str = "asset") -> str | None:
    CURRENT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    safe_prompt = _safe_filename(prompt)[:30] if prompt else "asset"
    filename = f"{datetime.now():%Y%m%d_%H%M%S}_{safe_prompt}.png"
    filepath = CURRENT_SESSION_DIR / filename

    headers_list = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.9",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://dashscope.aliyuncs.com/",
        },
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
        },
    ]

    try:
        api_key = get_api_key()
        if api_key:
            headers_list.insert(0, {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Authorization": f"Bearer {api_key}",
                "Referer": "https://dashscope.aliyuncs.com/",
            })
    except Exception:
        pass

    for headers in headers_list:
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
                if resp.status_code in (403, 429) and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                resp.raise_for_status()
                if len(resp.content) < 500:
                    time.sleep(2)
                    continue
                filepath.write_bytes(resp.content)
                if filepath.stat().st_size >= 500:
                    return str(filepath.resolve())
                filepath.unlink(missing_ok=True)
            except Exception:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))

    return None


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
        """生成2D游戏素材图片。仅在用户明确要求生成图片、画图、创作素材、制作图标时调用此工具。如果用户只是在聊天、提问、讨论，不要调用此工具。"""
        global _last_result
        _last_result = {"local_path": None, "remote_url": None}

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
            img_url = rsp.output.results[0].url
            _last_result["remote_url"] = img_url
            local_path = _immediate_download(img_url, prompt1)
            if local_path:
                _last_result["local_path"] = local_path
                return f"图片已生成并保存到本地：{local_path}"
            return f"图片已生成，远程URL：{img_url}（但下载到本地失败）"
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
        f"你是2D游戏素材生成助手，当前风格为「{style}」{cat_hint}。\n\n"
        "重要规则：\n"
        "- 只有当用户明确要求生成图片、画图、创作素材时，才调用 generate_image 工具\n"
        "- 如果用户只是在聊天、打招呼、提问、讨论游戏设计、询问建议等，直接用文字回复，不要调用任何工具\n"
        "- 判断依据：用户是否表达了「想要一张图片/素材」的意图\n\n"
        "回复简洁友好。生成图片成功后告知用户图片已就绪。"
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


def chat(executor: AgentExecutor, user_input: str) -> tuple[str, str | None, str | None]:
    """返回 (agent文本, 本地路径, 远程URL)"""
    global _last_result
    _last_result = {"local_path": None, "remote_url": None}

    result = executor.invoke({"input": user_input})
    output = result.get("output", str(result))

    local_path = _last_result.get("local_path")
    remote_url = _last_result.get("remote_url")

    if local_path and not Path(local_path).is_file():
        local_path = None

    return output, local_path, remote_url