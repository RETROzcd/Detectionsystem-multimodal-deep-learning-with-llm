import requests
import base64
from pathlib import Path
from typing import Optional, Union, Dict, Any


class DoubaoMultimodalClient:
    """火山引擎豆包多模态模型调用客户端"""

    def __init__(
        self,
        access_key: str,
            ?

    ):
        """
        初始化客户端
        
        :param access_key: 火山引擎Access Key ID
        :param base_url: 接口基础地址
        :param model: 模型名称
        :param default_temperature: 默认温度参数（0-1）
        :param default_max_tokens: 默认最大生成token数
        """
        self.access_key = access_key
        self.base_url = base_url
        self.model = model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._session = requests.Session()  # 复用会话提升性能

    def _encode_local_image(self, image_path: str) -> str:
        """将本地图片编码为base64字符串"""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_key}"
        }

    def chat(
        self,
        prompt: str,
        image_source: Optional[Union[str, Path]] = None,
        is_local_image: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送图文对话请求
        
        :param prompt: 用户提示文本
        :param image_source: 图片路径（本地）或URL（网络），None则为纯文本对话
        :param is_local_image: image_source是否为本地图片
        :param temperature: 温度参数（覆盖默认值）
        :param max_tokens: 最大生成token数（覆盖默认值）
        :return: 接口响应字典
        """
        try:
            # 构建消息体
            messages = [
                {
                    "role": "system",
                    "content": "你是豆包多模态助手，能理解图片并回答相关问题，回答简洁准确。"
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]

            # 添加图片内容
            if image_source:
                image_item = {"type": "image_url", "image_url": {}}
                
                if is_local_image:
                    # 处理本地图片
                    b64_str = self._encode_local_image(str(image_source))
                    image_item["image_url"]["url"] = f"data:image/jpeg;base64,{b64_str}"
                else:
                    # 处理网络图片
                    image_item["image_url"]["url"] = str(image_source)
                
                messages[1]["content"].append(image_item)

            # 构建请求参数
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens
            }

            # 发送请求
            response = self._session.post(
                url=self.base_url,
                json=payload,
                headers=self._build_headers()
            )
            response.raise_for_status()  # 抛出HTTP错误
            return {"success": True, "data": response.json()}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": str(response.json() if 'response' in locals() else None)
            }

    def get_answer(self, *args, **kwargs) -> Optional[str]:
        """
        简化接口：直接返回模型生成的回答文本
        
        :return: 回答文本（失败则返回None）
        """
        result = self.chat(*args, **kwargs)
        if result["success"]:
            return result["data"].get("choices", [{}])[0].get("message", {}).get("content")
        return None


# 使用示例
if __name__ == "__main__":
    # 初始化客户端（替换为你的Access Key）
    client = DoubaoMultimodalClient(
        access_key="ae2386e1-4f0a-42a1-8da5-f2c45a7e48a8",
        model="doubao-seed-1-6-250615"  # 确认已开通的多模态模型名称
    )

    # 1. 纯文本对话示例
    text_result = client.get_answer(prompt="请介绍一下人工智能的发展历程")
    print("文本回答：")
    print(text_result)
    print("-" * 50)

    # 2. 本地图片处理示例
    try:
        local_image_path = "test.jpg"  # 替换为实际图片路径
        image_result = client.get_answer(
            prompt="请描述这张图片的内容",
            image_source=local_image_path,
            is_local_image=True
        )
        print("本地图片分析结果：")
        print(image_result)
    except FileNotFoundError as e:
        print(f"图片处理失败：{e}")
    print("-" * 50)

    # 3. 网络图片处理示例（可选）
    # web_image_url = "https://example.com/sample.jpg"  # 替换为有效图片URL
    # web_result = client.get_answer(
    #     prompt="这张图片里有什么物体？",
    #     image_source=web_image_url,
    #     is_local_image=False
    # )
    # print("网络图片分析结果：")
    # print(web_result)