import gradio as gr
import base64

def get_img_html(img):
    if img is None:
        return "<div>请上传图片</div>"
    with open(img, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    # 每次都生成全新ID，防止iframe缓存
    import uuid
    img_id = f"zoom-img-{uuid.uuid4().hex}"
    html = f'''
    <div class="zoom-container">
        <img id="{img_id}" src="data:image/png;base64,{b64}" style="max-width:400px;">
        <div class="zoom-lens"></div>
        <div class="zoom-result"></div>
    </div>
    <script>
    (function(){{
        function initZoom() {{
            const img = document.getElementById('{img_id}');
            if (!img) {{
                setTimeout(initZoom, 300);
                return;
            }}
            const container = img.parentElement;
            const lens = container.querySelector('.zoom-lens');
            const result = container.querySelector('.zoom-result');
            const cx = result.offsetWidth / lens.offsetWidth;
            const cy = result.offsetHeight / lens.offsetHeight;
            result.style.backgroundImage = "url('" + img.src + "')";
            result.style.backgroundSize = (img.width * cx) + "px " + (img.height * cy) + "px";
            container.addEventListener("mousemove", moveLens);
            img.addEventListener("mousemove", moveLens);
            container.addEventListener("mouseenter", function() {{
                lens.style.display = "block";
                result.style.display = "block";
            }});
            container.addEventListener("mouseleave", function() {{
                lens.style.display = "none";
                result.style.display = "none";
            }});
            function moveLens(e) {{
                let pos, x, y;
                e.preventDefault();
                pos = getCursorPos(e);
                x = pos.x - (lens.offsetWidth / 2);
                y = pos.y - (lens.offsetHeight / 2);
                if (x > img.width - lens.offsetWidth) {{x = img.width - lens.offsetWidth;}}
                if (x < 0) {{x = 0;}}
                if (y > img.height - lens.offsetHeight) {{y = img.height - lens.offsetHeight;}}
                if (y < 0) {{y = 0;}}
                lens.style.left = x + "px";
                lens.style.top = y + "px";
                result.style.left = (e.pageX + 20) + "px";
                result.style.top = (e.pageY - 150) + "px";
                result.style.backgroundPosition = "-" + (x * cx) + "px -" + (y * cy) + "px";
            }}
            function getCursorPos(e) {{
                let a, x = 0, y = 0;
                e = e || window.event;
                a = img.getBoundingClientRect();
                x = e.pageX - a.left;
                y = e.pageY - a.top;
                x = x - window.pageXOffset;
                y = y - window.pageYOffset;
                return {{x : x, y : y}};
            }}
        }}
        setTimeout(initZoom, 200);
    }})();
    </script>
    <style>
    .zoom-container {{
        position: relative;
        width: fit-content;
        display: inline-block;
    }}
    .zoom-lens {{
        position: absolute;
        border: 2px solid #d4d4d4;
        width: 100px;
        height: 100px;
        background-repeat: no-repeat;
        display: none;
        cursor: none;
    }}
    .zoom-result {{
        position: fixed;
        border: 1px solid #d4d4d4;
        width: 300px;
        height: 300px;
        background-repeat: no-repeat;
        display: none;
        z-index: 999;
        box-shadow: 0 0 10px rgba(0,0,0,0.3);
    }}
    </style>
    '''
    return html

with gr.Blocks() as demo:
    gr.Markdown("# 图片悬停放大演示")
    with gr.Row():
        with gr.Column():
            img_input = gr.Image(label="上传图片", type="filepath")
            html_out = gr.HTML()
    img_input.change(get_img_html, inputs=img_input, outputs=html_out)

if __name__ == '__main__':
    demo.launch() 