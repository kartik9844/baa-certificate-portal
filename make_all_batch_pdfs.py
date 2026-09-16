from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

root = Path(__file__).resolve().parent
src = root / 'certificates'
out_root = root / 'pdf_batches'
files = sorted(src.glob('*.jpg'))
for i in range(0, len(files), 50):
    batch_no = i // 50 + 1
    out = out_root / f'batch_{batch_no:03d}'
    out.mkdir(parents=True, exist_ok=True)
    for jpg in files[i:i+50]:
        pdf = out / f'{jpg.stem}.pdf'
        if pdf.exists() and pdf.stat().st_size > 0:
            continue
        with Image.open(jpg) as im:
            w, h = im.size
        c = canvas.Canvas(str(pdf), pagesize=(w, h), pageCompression=1)
        c.drawImage(ImageReader(str(jpg)), 0, 0, width=w, height=h, preserveAspectRatio=True, mask='auto')
        c.showPage()
        c.save()
print(f'created_or_present={len(files)} batches={(len(files)+49)//50}')
