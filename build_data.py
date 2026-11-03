"""Đọc file Word -> data.json (sản phẩm, sự kiện, luật) + trích ảnh sản phẩm."""
import re, json, sys, os, docx

SRC = sys.argv[1]
os.makedirs('static/img', exist_ok=True)
d = docx.Document(SRC)
head_re = re.compile(r'^\s*(?:SP\s*)?(\d{1,2})\.?\s+(.+)$')
products, cur = {}, None
FIELDS = [('Mô tả','mo_ta'),('Ngân sách','ngan_sach'),('Số người sử dụng','so_nguoi'),
          ('Nguồn nước đầu vào','nguon_nuoc'),('Vị trí lắp đặt','vi_tri'),
          ('Nhu cầu sử dụng','nhu_cau'),('Hãng sản xuất','hang'),('Công nghệ lọc','cong_nghe'),
          ('Nhu cầu bảo trì','bao_tri'),('Số vòi','so_voi'),('Số vòi nước','so_voi'),('Vòi','so_voi')]
EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'

for p in d.paragraphs:
    txt = p.text.strip()
    if txt.startswith('2. XÂY DỰNG'):
        break
    m = head_re.match(txt)
    if m and ('Máy lọc' in txt or 'Karofi' in txt) and len(txt) < 90 and 'Mô tả' not in txt:
        cur = int(m.group(1))
        products[cur] = {'id': f'SP{cur}', 'ten': m.group(2).strip(), 'img': []}
        continue
    if cur is None:
        continue
    for blip in p._p.xpath('.//a:blip'):
        products[cur]['img'].append(blip.get(EMBED))
    if not txt:
        continue
    t = re.sub(r'^[\-–•]\s*', '', txt)
    t = re.sub(r'^Mô tả\s*:\s*Mô tả\s*:', 'Mô tả:', t)
    hit = False
    for label, key in FIELDS:
        mm = re.match(rf'^{label}\s*:\s*(.*)$', t, re.I)
        if mm:
            products[cur][key] = (products[cur].get(key, '') + ' ' + mm.group(1)).strip()
            hit = True
            break
    if not hit and re.match(r'^(\d\s*vòi|1 vòi|2 vòi)', t):
        products[cur]['so_voi'] = t

# sửa trường hợp 'Ngân sách' dính vào cuối mô tả
for pr in products.values():
    mt = pr.get('mo_ta', '')
    mm = re.search(r'\s*Ngân sách\s*:\s*(.*)$', mt)
    if mm:
        pr['mo_ta'] = mt[:mm.start()].strip()
        pr.setdefault('ngan_sach', mm.group(1).strip())
    for k in ('mo_ta', 'ngan_sach'):
        if k in pr:
            pr[k] = re.sub(r'(\w)\.(Ngân|Số)', r'\1. \2', pr[k])

# xuất ảnh
for n, pr in products.items():
    files = []
    for i, rid in enumerate(pr['img']):
        part = d.part.related_parts[rid]
        ext = os.path.splitext(part.partname)[1] or '.jpg'
        fn = f'sp{n}_{i+1}{ext}'
        with open(f'static/img/{fn}', 'wb') as f:
            f.write(part.blob)
        files.append(fn)
    pr['img'] = files

# tập sự kiện
text = '\n'.join(p.text for p in d.paragraphs)
facts, group = {}, None
sec = text.split('2.1. Tập sự kiện')[1].split('2.2. Xây dựng tập luật')[0]
for line in sec.split('\n'):
    line = line.strip()
    g = re.match(r'^2\.1\.\d+\.\s*(.+?)\s*\((\w+)\)$', line)
    if g:
        group = g.group(2)
        facts[group] = {'ten': g.group(1), 'opts': []}
        continue
    f = re.match(r'^\+\s*(.+?)\s*→\s*(\w+)$', line)
    if f and group and group != 'SP':
        facts[group]['opts'].append({'ma': f.group(2), 'nhan': f.group(1)})
facts.pop('SP', None)

# tập luật
rules, lines = [], text.split('\n')
for i, l in enumerate(lines):
    m = re.match(r'^(\d+)\.\s*Nếu\s+(.*)$', l.strip())
    if m and i + 1 < len(lines):
        sym = re.match(r'^\s*(.+?)\s*→\s*(SP\d+)\s*$', lines[i + 1].strip())
        if sym:
            conds = [c.strip() for c in sym.group(1).split('⋀')]
            rules.append({'id': int(m.group(1)),
                          'dien_giai': l.strip().split('. ', 1)[1],
                          'dk': conds, 'kq': sym.group(2)})

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump({'products': {f'SP{n}': v for n, v in sorted(products.items())},
               'facts': facts, 'rules': rules}, f, ensure_ascii=False, indent=1)
print(len(products), 'sản phẩm;', len(rules), 'luật')