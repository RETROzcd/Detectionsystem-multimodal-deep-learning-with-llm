class Visualization:

    def __init__(self) -> None:
        pass
    
    # draw result
    def show_ocr(self, image, result):
        image = Image.fromarray(np.uint8(image)).convert('RGB')
        #image = Image.open(img_path).convert('RGB')
        boxes = [line["box"] for line in result]
        txts = [line["txt"] for line in result]
        scores = [line["score"] for line in result]
        im_show = draw_ocr(image, boxes, txts, scores, font_path='./PaddleOCR/doc/fonts/simfang.ttf')
        #im_show = draw_ocr(image, boxes, txts, scores)
        im_show = Image.fromarray(im_show)
        im_show.save('result.jpg')