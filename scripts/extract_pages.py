import fitz
import os

output_dir = 'sepp-housing-2021-pages'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

doc = fitz.open('sepp_housing_2021.pdf')
print('Total pages:', len(doc))

pages = {35: 'infill_affordable', 47: 'seniors_independent', 72: 'tod_affordable'}

for page_num, name in pages.items():
    page = doc[page_num - 1]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    output = os.path.join(output_dir, 'page-' + str(page_num) + '_' + name + '.png')
    pix.save(output)
    size = os.path.getsize(output) / 1024
    print('Page', page_num, 'saved:', round(size, 1), 'KB')

for page_num in range(100, min(120, len(doc))):
    text = doc[page_num].get_text().lower()
    if 'accessible area means' in text:
        page = doc[page_num]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        output = os.path.join(output_dir, 'page-' + str(page_num + 1) + '_accessible_area_def.png')
        pix.save(output)
        size = os.path.getsize(output) / 1024
        print('Schedule 10 page', page_num + 1, 'saved:', round(size, 1), 'KB')
        break

doc.close()
print('All pages extracted!')
