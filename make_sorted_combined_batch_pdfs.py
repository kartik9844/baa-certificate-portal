from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

root = Path(__file__).resolve().parent
src = root / 'sorted_certificates'
out = root / 'sorted_batch_pdfs'
out.mkdir(parents=True, exist_ok=True)
files = sorted(src.glob('*.jpg'))
for i in range(0, len(files), 50):
    batch_no = i // 50 + 1
    target = out / f'Batch_{batch_no:03d}.pdf'
    c = None
    for jpg in files[i:i+50]:
        with Image.open(jpg) as im:
            w, h = im.size
        if c is None:
            c = canvas.Canvas(str(target), pagesize=(w, h), pageCompression=1)
        c.setPageSize((w, h))
        c.drawImage(ImageReader(str(jpg)), 0, 0, width=w, height=h, preserveAspectRatio=True, mask='auto')
        c.showPage()
    if c is not None:
        c.save()
print(f'created={((len(files)+49)//50)} batches pages={len(files)} output={out}')
