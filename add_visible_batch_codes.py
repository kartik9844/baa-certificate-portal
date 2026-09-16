from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parent
source = root / '2025 TEM - CERTIFICATE ISSUE_SORTED_ASSIGNED.xlsx'
output = root / '2025 TEM - CERTIFICATE ISSUE_SORTED_WITH_BATCH_CODES.xlsx'
main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('', main)
ns = {'m': main}

with ZipFile(source) as zin:
    sheet = ET.fromstring(zin.read('xl/worksheets/sheet1.xml'))
    sheet_data = sheet.find('m:sheetData', ns)
    rows = sheet_data.findall('m:row', ns)
    header = rows[0]
    old_h = header.find("m:c[@r='H1']", ns)
    if old_h is not None:
        header.remove(old_h)
    h = ET.SubElement(header, f'{{{main}}}c', {'r': 'H1', 't': 'inlineStr'})
    is_el = ET.SubElement(h, f'{{{main}}}is')
    ET.SubElement(is_el, f'{{{main}}}t').text = 'BATCH PDF'
    for row in rows[1:]:
        rnum = int(row.attrib['r'])
        cell = row.find(f"m:c[@r='H{rnum}']", ns)
        if cell is not None:
            row.remove(cell)
        cell = ET.SubElement(row, f'{{{main}}}c', {'r': f'H{rnum}', 't': 'inlineStr'})
        is_el = ET.SubElement(cell, f'{{{main}}}is')
        ET.SubElement(is_el, f'{{{main}}}t').text = f'Batch_{((rnum - 2) // 50) + 1:03d}.pdf'
    sheet_bytes = ET.tostring(sheet, encoding='utf-8', xml_declaration=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = sheet_bytes if item.filename == 'xl/worksheets/sheet1.xml' else zin.read(item.filename)
            zout.writestr(item, data)
print(f'created={output}')
