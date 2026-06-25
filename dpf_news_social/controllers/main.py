import base64
import io
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

MIN_RATIO = 0.8   # 4:5 portrait
MAX_RATIO = 1.91  # 1.91:1 landscape


class InstagramImageController(http.Controller):

    @http.route('/dpf/instagram/image/<int:image_id>', type='http', auth='public', methods=['GET'])
    def instagram_image(self, image_id, **kwargs):
        img_rec = request.env['news.post.image'].sudo().browse(image_id)
        if not img_rec.exists() or not img_rec.image:
            return request.not_found()

        try:
            from PIL import Image

            img_data = base64.b64decode(img_rec.image)
            img = Image.open(io.BytesIO(img_data)).convert('RGB')
            w, h = img.size
            ratio = w / h

            if ratio < MIN_RATIO:
                # Too tall — crop height to 4:5
                new_h = int(w / MIN_RATIO)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))
            elif ratio > MAX_RATIO:
                # Too wide — crop width to 1.91:1
                new_w = int(h * MAX_RATIO)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))

            # Scale down to max 1080px width
            if img.width > 1080:
                new_h = int(1080 * img.height / img.width)
                img = img.resize((1080, new_h), Image.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            image_bytes = buffer.getvalue()

        except ImportError:
            _logger.warning('Pillow not installed, serving original image')
            image_bytes = base64.b64decode(img_rec.image)
        except Exception as e:
            _logger.error('DPF image crop error: %s', e)
            image_bytes = base64.b64decode(img_rec.image)

        return request.make_response(image_bytes, headers=[
            ('Content-Type', 'image/jpeg'),
            ('Content-Length', str(len(image_bytes))),
            ('Cache-Control', 'public, max-age=86400'),
        ])
