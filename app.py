"""Hệ chuyên gia tư vấn mua máy lọc nước (Flask)."""
import json, os
from flask import Flask, render_template, request

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, 'data.json'), encoding='utf-8') as f:
    DATA = json.load(f)

PRODUCTS, FACTS, RULES = DATA['products'], DATA['facts'], DATA['rules']
GROUPS = list(FACTS.keys())
LABEL = {o['ma']: o['nhan'] for g in FACTS.values() for o in g['opts']}

app = Flask(__name__)


def group_of(code):
    return ''.join(c for c in code if c.isalpha())


def infer(facts):
    """Suy diễn tiến trên tập luật.
    - Luật khớp hoàn toàn: mọi điều kiện đều bằng sự kiện người dùng chọn.
    - Mã kết thúc bằng 0 ('chưa xác định') = không ràng buộc.
    - Nếu không có luật khớp hoàn toàn: xếp hạng theo số tiêu chí khớp.
    Mỗi sản phẩm chỉ giữ luật tốt nhất."""
    best = {}
    for r in RULES:
        matched, exact = 0, True
        for cond in r['dk']:
            user = facts.get(group_of(cond))
            if user == cond:
                matched += 1
            elif user is None or user.endswith('0'):
                matched += 1
                if user is not None and cond != user:
                    exact = False
            else:
                exact = False
        entry = {'rule': r, 'matched': matched, 'total': len(r['dk']), 'exact': exact}
        cur = best.get(r['kq'])
        if cur is None or (exact, matched) > (cur['exact'], cur['matched']):
            best[r['kq']] = entry
    results = [e for e in best.values() if e['matched'] >= 6]
    results.sort(key=lambda e: (-e['exact'], -e['matched'], e['rule']['id']))
    return results


@app.route('/')
def index():
    return render_template('index.html', facts=FACTS, groups=GROUPS)


@app.route('/tu-van', methods=['POST'])
def advise():
    chosen = {g: request.form.get(g) for g in GROUPS if request.form.get(g)}
    results = infer(chosen)
    exact = [e for e in results if e['exact']]
    shown = (exact if exact else results)[:5]
    return render_template('result.html', chosen=chosen, label=LABEL, facts=FACTS,
                           groups=GROUPS, results=shown, products=PRODUCTS,
                           has_exact=bool(exact))


@app.route('/san-pham')
def catalog():
    hang = request.args.get('hang', '')
    items = [p for p in PRODUCTS.values() if not hang or hang.lower() in p['ten'].lower()]
    brands = ['Kangaroo', 'Karofi', 'Sunhouse', 'Toshiba', 'A. O. Smith', 'Mutosi', 'Korihome', 'Hòa Phát']
    return render_template('catalog.html', items=items, brands=brands, hang=hang)


@app.route('/san-pham/<sp>')
def product(sp):
    p = PRODUCTS.get(sp.upper())
    if not p:
        return render_template('404.html'), 404
    rules = [r for r in RULES if r['kq'] == p['id']]
    return render_template('product.html', p=p, rules=rules)


@app.route('/tap-luat')
def rules_page():
    q = request.args.get('sp', '')
    items = [r for r in RULES if not q or r['kq'] == q]
    return render_template('rules.html', rules=items, products=PRODUCTS, sel=q)


if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000, debug=True)