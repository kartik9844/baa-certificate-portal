from pathlib import Path
from pypdf import PdfWriter, PdfReader

root = Path(__file__).resolve().parent
src = root / 'pdf_batches'
out = root / 'combined_batch_pdfs'
out.mkdir(parents=True, exist_ok=True)
files = sorted(src.rglob('*.pdf'))
for i in range(0, len(files), 50):
    batch_no = i // 50 + 1
    target = out / f'Batch_{batch_no:03d}.pdf'
    writer = PdfWriter()
    for pdf in files[i:i+50]:
        writer.append(PdfReader(str(pdf)))
    with target.open('wb') as f:
        writer.write(f)
print(f'created={((len(files)+49)//50)} batches pages={len(files)} output={out}')
