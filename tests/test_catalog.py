import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('catalog', Path(__file__).parents[1] / 'scripts' / 'build_catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

class CatalogTests(unittest.TestCase):
    def product(self, price, name='Test pillow', description='枕头/只 南通 私有供应商 电话123456', **extra):
        return {'Unit Price (CNY)':price, 'Unit Cost':'SECRET_COST', 'Product Name':name,
                'Product Name (Chinese)':description, 'SKU':'PRIVATE_SKU', **extra}

    def test_public_allowlist_and_price_source(self):
        item=catalog.build_catalog([self.product('100')])['products'][0]
        self.assertEqual(set(item), catalog.PUBLIC_KEYS)
        self.assertEqual((item['priceMin'],item['priceMax']),(85,115))
        self.assertEqual(item['nameZh'],'枕头')
        self.assertEqual(item['location'],'Nantong, Jiangsu, China')
        self.assertNotIn('SECRET',str(item))
        self.assertNotIn('私有供应商',str(item))

    def test_variant_aggregation_and_decimal_comma(self):
        items=catalog.build_catalog([self.product('10'),self.product('20'),self.product('248,5','Other')])['products']
        pillow=next(p for p in items if p['name']=='Test pillow')
        self.assertEqual((pillow['priceMin'],pillow['priceMax']),(8.5,23))
        other=next(p for p in items if p['name']=='Other')
        self.assertEqual((other['priceMin'],other['priceMax']),(211.22,285.78))

    def test_missing_values_and_different_locations(self):
        items=catalog.build_catalog([self.product('',description='枕头'),self.product('100',description='枕头/只 杭州')])['products']
        self.assertEqual(len(items),2)
        missing=next(p for p in items if not p['location'])
        self.assertIsNone(missing['priceMin'])
        self.assertIsNone(missing['priceMax'])

    def test_only_supported_price_formats(self):
        for price in ['-15','1e3','model 123','10 x 20','Free','0']:
            self.assertEqual(catalog.prices(price),[])
        self.assertEqual(catalog.prices('40.5 / 48'),[catalog.Decimal('40.5'),catalog.Decimal('48')])
        self.assertEqual(catalog.prices('XL - 760'),[catalog.Decimal(760)])

    def test_buyer_notes_removed(self):
        item=catalog.build_catalog([self.product('1',name='Toothpaste (i bought this myself on alibaba)')])['products'][0]
        self.assertEqual(item['name'],'Toothpaste')

if __name__=='__main__': unittest.main()
