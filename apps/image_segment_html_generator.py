import base64
import os
import logging
class ImageSegmentHtmlGenerator:
    def __init__(self):
        pass

    def generate_html(self, image_paths):
        img_urls = []
        for idx, image_path in enumerate(image_paths):
            with open(image_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
                # 假设都是jpg图片，如有png请自行调整
                img_url = f"data:image/jpeg;base64,{encoded_string}"
                img_urls.append(img_url)
        html_code = """
        <div style='display: flex; flex-wrap: wrap; gap: 24px;'>
        """
        for i, img_url in enumerate(img_urls):
            html_code += f'''
            <div style="display: flex; flex-direction: column; align-items: center;">
            <img id="toggle-img-{i}" src="{img_url}"
                style="width:30px; transition: width 0.3s; cursor:pointer; border:1px solid #ccc; border-radius:8px; margin-bottom:8px;"
                onclick="if(this.style.width === '30px'){{this.style.width='600px';}}else{{this.style.width='30px';}}">
            <div style="color: #888;">点击图片放大/缩小</div>
            </div>
            '''
        html_code += "</div>"
        return html_code