import base64
import os
from openai import OpenAI
from openai import AzureOpenAI
import logging
from agents.agent_utils import call_multi_conservations_openai_llm
import time, json
import traceback
from agents.image_cut.models.vlm_cut_prompt import IMAGE_CUT_PROMPT
from agents.agent_utils import draw_yolo_boxes
from agents.agent_utils import ModelType

'''
    模式1: 一次上传多张图片, 多次ask: upload_images -> ask[1]->ask[1]...

    模式2: 一次上传一张，多次ask: upload_image -> ask[1]->ask[1]... -> clear -> upload_image -> ask[1]->ask[1]... 
'''
class SingleImageVlmModel:

    def __init__(self, model_configs):
        self._model_name = model_configs['model_name']
        if self._model_name in [ModelType.GPT_4O, ModelType.O4_MINI, ModelType.O3_MINI]:
            self._client = AzureOpenAI(
                  ?
                )
        elif self._model_name in [ModelType.QWEN_VL_MAX]:
            self._client = OpenAI(
             ?)
        else:
            raise ValueError(f"Invalid model name: {self._model_name}")
        self.messages = []
        self.image_count = 0
        # 给大模型的最大边的分辨率
        self.max_image_size = model_configs['max_image_size'] if 'max_image_size' in model_configs else -1

    def clear_context(self):
        self.messages.clear()

    def upload_image(self, image_path, metadata=None):
        try:
            # 先检查图片的大小的最长边大于self.max_image_size，如果大于则对图片进行resize至最长边不超过self.max_image_size，然后再转成base64
            from PIL import Image
            import io
            if self.max_image_size > 0:
                with Image.open(image_path) as img:
                    width, height = img.size
                    max_side = max(width, height)
                    if max_side > self.max_image_size:
                        # 计算缩放比例
                        scale = self.max_image_size / max_side
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # 将图片保存到内存中
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG")
                    buffered.seek(0)
                    base64_image = base64.b64encode(buffered.read()).decode("utf-8")
            else:
                with Image.open(image_path) as img:
                    width, height = img.size
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG")
                    buffered.seek(0)
                    base64_image = base64.b64encode(buffered.read()).decode("utf-8")

            self.image_count += 1
            image_tag = f"Image {self.image_count}:"

            # 构建元信息文本
            meta_text = ""
            if metadata:
                meta_text += "\n".join([f"{k.capitalize()}: {v}" for k, v in metadata.items()])
                meta_text = "Metadata:\n" + meta_text + "\n\n"

            content = [
                {"type": "text", "text": f"{image_tag}\n{meta_text}"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    },
                },
            ]

            self.messages.append({
                "role": "user",
                "content": content
            })
            return True, (width, height)
        except Exception as e:
            traceback.print_exc()
            logging.error(f"❌ Error uploading image: {e}, image_path={image_path}")
            return False, (0, 0)

    '''
        返回: status, answer, usage
    '''
    def ask(self, question, add2context=False):
        """向模型提问，并获取回答"""
        # if not self.image_count:
        #     logging.error("⚠️ No images uploaded yet.")
        #     return False, "", {}

        full_question = (
            f"Question: {question}"
        )
        my_messages = self.messages.copy()
        my_messages.append({
                "role": "user",
                "content": [{"type": "text", "text": full_question}]
            })
        try:
            response = call_multi_conservations_openai_llm(self._client, self._model_name, my_messages)
            if response is not None:
                answer = response.choices[0].message.content
                usage = response.usage
                my_messages.append({"role": "assistant", "content": answer})
                if add2context:
                     self.messages = my_messages
                return True, answer, usage
            else:
                return False, "Error: No response from Azure OpenAI", {}
        except Exception as e:
            logging.error(f"Error calling Azure OpenAI: {e}")
            return False,f"Error: {str(e)}", {}

if __name__ == "__main__":
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/single_image_vlm.log"),
            logging.StreamHandler()
        ],
        force=True
    )
    model_configs = {
          ?
                }
    model_configs = {
             ?
                }
    vlm_model = SingleImageVlmModel(model_configs)
    image_paths_with_metadata = ("./work_dir/100/包装图/original/外包装_page_1.jpg", {"source": "外包装图"})
    vlm_model.upload_image(*image_paths_with_metadata)
    image_cut_prompt = "这是一个产品的外包装图， 包装图一共有6面，请根据根据整体布局和分割线(实线、虚线)将其分解成不同的面，按yolo格式的每个面的坐标值。"
    image_cut_prompt = IMAGE_CUT_PROMPT['image_cut_v1']
    questions = [image_cut_prompt]
    for qid, question in enumerate(questions):
        status, answer, usage = vlm_model.ask(question)
        logging.info(f"{qid}. question: {question}, answer: {answer}")
        if status:
            json_answer = json.loads(answer)
            bounding_boxes = json_answer['boundingboxes'] if 'boundingboxes' in json_answer else []
            bounding_boxes =  [
                               [0.1, 0.5, 0.15, 0.8],
                               [0.9, 0.5, 0.15, 0.8],
                               [0.5, 0.5, 0.6, 0.8],
                               [0.5, 0.1, 0.6, 0.3],
                               [0.5, 0.1, 0.6, 0.15],
                               [0.5, 0.9, 0.6, 0.15]
                             ]

            logging.info(f"bounding_boxes: {bounding_boxes}")
            # 渲染bounding_boxes到图片上并保存
            image_path = image_paths_with_metadata[0]
            output_path = image_path.replace(".jpg", "_with_boxes.jpg")
            draw_yolo_boxes(image_path, bounding_boxes, output_path)
            logging.info(f"Rendered image with bounding boxes saved to: {output_path}")

            