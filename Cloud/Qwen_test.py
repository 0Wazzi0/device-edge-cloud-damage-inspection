from openai import OpenAI
import os
import base64

def encode_image_to_base64(image_path):
    """将本地图片编码为Base64格式"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return f"data:image/jpeg;base64,{encoded_string.decode('utf-8')}"

# 初始化OpenAI客户端
api_key = os.getenv("DASHSCOPE_API_KEY")  # 使用环境变量中的API密钥
if not api_key:
    print("警告：未设置DASHSCOPE_API_KEY环境变量")
    api_key = input("请输入API密钥: ")

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


# 设置要分析的图片路径
image_path = "d:\\.code\\Python3d11d8\\images\\results_testImage2.jpg"

# 检查图片文件是否存在
if not os.path.exists(image_path):
    print(f"错误：找不到图片文件 {image_path}")
    exit(1)

# 编码本地图片
image_base64 = encode_image_to_base64(image_path)

# 创建聊天完成请求
completion = client.chat.completions.create(
    model="qwen3-vl-plus",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64  # 使用Base64编码的图片
                    },
                },
                {
                    "type": "text", 
                    "text": """你是一个经验丰富的交警，根据输入的图片，分析其中的车损并根据以下JSON结构输出结果：
                    {
                        "车损类别" : "",
                        "车损等级" : "",
                        "图像描述" : "",
                        "车损综合描述" : "",
                        "是否需要人工介入" : ""
                    }
                    要求：
                    1."车损类别"：如"剐蹭","撞击凹陷","车门脱落"等。
                    2."车损等级"：根据轻微到严重分为五个程度，输出等级数字，对应
                        {
                            "1" = (轻微损伤),
                            "2" = (一般损伤),
                            "3" = (较严重损伤),
                            "4" = (严重损伤)，
                            "5" = (完全损坏)
                        }
                    3.图像描述：如"清晰可见"、"模糊不清"。
                    4."车损综合描述" :如"无需交警介入"、"需要交警介入"、"需要人工进一步分析"
                    5."是否需要人工介入" : 如"是"、"否"。"""},  # 车损分析的 prompt
            ],
        },
    ],
    stream=True,
    # enable_thinking 参数开启思考过程，thinking_budget 参数设置最大推理过程 Token 数
    extra_body={
        'enable_thinking': True,
        "thinking_budget": 81920},
)

print("\n" + "=" * 20 + "车损分析结果" + "=" * 20 + "\n")

for chunk in completion:
    # 如果chunk.choices为空，则打印usage
    if not chunk.choices:
        print("\nUsage:")
        print(chunk.usage)
    else:
        delta = chunk.choices[0].delta
        # 打印回复内容
        if delta.content:
            print(delta.content, end='', flush=True)