"""Build an allowlisted public catalog from a PRIVATE Products CSV / connector JSON.

Input must be kept outside the website/repository. Only sanitized product titles,
city-level locations, and widened price bounds are written to the public output.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_CEILING
from pathlib import Path

CITIES = {
    '温州': ('Wenzhou', 'Zhejiang'), '清远': ('Qingyuan', 'Guangdong'),
    '杭州': ('Hangzhou', 'Zhejiang'), '宁波': ('Ningbo', 'Zhejiang'),
    '通州': ('Tongzhou', None), '南通': ('Nantong', 'Jiangsu'),
    '深圳': ('Shenzhen', 'Guangdong'), '广州': ('Guangzhou', 'Guangdong'),
    '佛山': ('Foshan', 'Guangdong'), '福安': ('Fu’an', 'Fujian'),
    '金华': ('Jinhua', 'Zhejiang'), '常熟': ('Changshu', 'Jiangsu'),
    '石家庄': ('Shijiazhuang', 'Hebei'), '萍乡': ('Pingxiang', 'Jiangxi'),
    '青岛': ('Qingdao', 'Shandong'), '东台': ('Dongtai', 'Jiangsu'),
    '东莞': ('Dongguan', 'Guangdong'), '宿迁': ('Suqian', 'Jiangsu'),
    '淮安': ('Huai’an', 'Jiangsu'), '衡水': ('Hengshui', 'Hebei'),
    '南宁': ('Nanning', 'Guangxi'), '惠州': ('Huizhou', 'Guangdong'),
    '赣州': ('Ganzhou', 'Jiangxi'), '厦门': ('Xiamen', 'Fujian'),
    '桐乡': ('Tongxiang', 'Zhejiang'), '天津': ('Tianjin', None),
    '中山': ('Zhongshan', 'Guangdong'), '邢台': ('Xingtai', 'Hebei'),
    '廊坊': ('Langfang', 'Hebei'), '盖州': ('Gaizhou', 'Liaoning'),
    '上海': ('Shanghai', None), '绍兴': ('Shaoxing', 'Zhejiang'),
    '台州': ('Taizhou', 'Zhejiang'), '丽水': ('Lishui', 'Zhejiang'),
    '苏州': ('Suzhou', 'Jiangsu'), '莆田': ('Putian', 'Fujian'),
    '宁德': ('Ningde', 'Fujian'), '合肥': ('Hefei', 'Anhui'),
    '常州': ('Changzhou', 'Jiangsu'), '德州': ('Dezhou', 'Shandong'),
}
REQUIRED = ('Unit Price (CNY)', 'Product Name', 'Product Name (Chinese)')
PUBLIC_KEYS = {'id', 'name', 'nameZh', 'location', 'locationZh', 'priceMin', 'priceMax', 'currency'}


def prices(value):
    """Accept explicit numeric prices, decimal commas, slash options and size prefixes.
    Never extract arbitrary numbers from commentary, models or dimensions.
    """
    text = str(value).strip()
    if not text:
        return []
    text = re.sub(r'^(?:CNY|RMB|¥|￥)\s*', '', text, flags=re.I)
    text = re.sub(r'^(?:M|XL|XXL)\s*(?:-\s*)?(?=\d)', '', text, flags=re.I)
    result = []
    for part in text.split('/'):
        part = part.strip()
        if not re.fullmatch(r'\d+(?:[.,]\d+)?', part):
            return []
        try:
            value = Decimal(part.replace(',', '.'))
            if value <= 0 or value > 10000000:
                return []
            result.append(value)
        except InvalidOperation:
            return []
    return result


def clean_name(value):
    name = re.sub(r'\s+', ' ', str(value)).strip()
    # Remove known buyer instructions, retaining meaningful size/color variants.
    name = re.sub(r'\([^)]*(?:i bought|please try|can (?:it|this|you)|could you|no logo)[^)]*\)', '', name, flags=re.I)
    name = re.sub(r'\s*No logo or name anywhere on it please.*$', '', name, flags=re.I)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:180]


def chinese_name(value):
    # The description suffix can contain factory names and private packing notes.
    name = re.split(r'[/／（(\n\r]', str(value), maxsplit=1)[0].strip()
    for city in CITIES:
        name = name.split(city)[0]
    name = re.sub(r'\d+(?:\.\d+)?元.*$', '', name).strip()
    if re.search(r'仓库|贴标|条形码|需要|我自己|购买|换彩盒|不用', name):
        return ''
    return name[:60]


def supplier_location(description):
    found = [city for city in CITIES if city in str(description)]
    if len(found) != 1:
        return '', ''
    city = found[0]
    english, province = CITIES[city]
    return f'{english}, {province}, China' if province else f'{english}, China', city


def build_catalog(rows):
    grouped = {}
    for row in rows:
        name = clean_name(row.get('Product Name', ''))
        if not name:
            continue
        description = row.get('Product Name (Chinese)', '')
        location, location_zh = supplier_location(description)
        # Same title and location can represent multiple recorded variants.
        key = (name.casefold(), location)
        if key not in grouped:
            grouped[key] = {'name': name, 'nameZh': chinese_name(description), 'location': location,
                            'locationZh': location_zh, '_prices': []}
        grouped[key]['_prices'].extend(prices(row.get('Unit Price (CNY)', '')))
        if not grouped[key]['nameZh']:
            grouped[key]['nameZh'] = chinese_name(description)
    products = []
    for key, item in sorted(grouped.items()):
        values = item.pop('_prices')
        low = (min(values) * Decimal('.85')).quantize(Decimal('.01'), rounding=ROUND_FLOOR) if values else None
        high = (max(values) * Decimal('1.15')).quantize(Decimal('.01'), rounding=ROUND_CEILING) if values else None
        item.update(id=hashlib.sha256('\0'.join(key).encode()).hexdigest()[:16],
                    priceMin=float(low) if low is not None else None,
                    priceMax=float(high) if high is not None else None, currency='CNY')
        assert set(item) == PUBLIC_KEYS
        products.append(item)
    if not products:
        raise ValueError('No named products found; refusing to replace the catalog.')
    return {'schemaVersion': 1, 'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'currency': 'CNY', 'products': products}


def read_source(path):
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not all(key in (reader.fieldnames or []) for key in REQUIRED):
                raise ValueError('Expected Products tab headers were not found.')
            return list(reader)
    data = json.loads(path.read_text(encoding='utf-8'))
    values = data.get('values', [])
    if not values or not all(key in values[0] for key in REQUIRED):
        raise ValueError('Expected Products tab headers were not found.')
    headers = values[0]
    return [dict(zip(headers, row)) for row in values[1:]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', default=Path('data/products.json'), type=Path)
    args = parser.parse_args()
    catalog = build_catalog(read_source(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(args.output)
    print(f'Published {len(catalog["products"])} sanitized product entries.')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError):
        print('Catalog update failed. Check the private input and headers; existing catalog was preserved.', file=sys.stderr)
        raise SystemExit(1)
