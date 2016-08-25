# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import datetime
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool
from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart


def create_supplier(company):
    pool = Pool()
    Account = pool.get('account.account')
    Template = pool.get('product.template')
    Uom = pool.get('product.uom')
    ProductSupplier = pool.get('purchase.product_supplier')
    Party = pool.get('party.party')

    u, = Uom.search([('name', '=', 'Unit')])
    template, = Template.create([{
                'name': 'Product',
                'default_uom': u.id,
                'purchase_uom': u.id,
                'list_price': Decimal(0),
                'cost_price': Decimal(10),
                'products': [('create', [{}])],
                }])
    product, = template.products

    # Prepare supplier
    receivable, = Account.search([
        ('kind', '=', 'receivable'),
        ('company', '=', company.id),
        ])
    payable, = Account.search([
        ('kind', '=', 'payable'),
        ('company', '=', company.id),
        ])
    supplier, = Party.create([{
                'name': 'supplier',
                'account_receivable': receivable.id,
                'account_payable': payable.id,
                }])

    # Prepare product supplier
    product_supplier, = ProductSupplier.create([{
                'product': template.id,
                'company': company.id,
                'party': supplier.id,
                'lead_time': datetime.timedelta(days=2),
                }])
    return supplier, product_supplier


class PurchaseSupplierDiscountTestCase(ModuleTestCase):
    'Test Purchase Supplier Discount module'
    module = 'purchase_supplier_discount'

    @with_transaction()
    def test_update_price(self):
        'Test update price'
        ProductSupplierPrice = Pool().get('purchase.product_supplier.price')

        company = create_company()
        with set_company(company):
            create_chart(company)
            supplier, product_supplier = create_supplier(company)

            # Create supplier price defining unit price and not gross unit
            # price (support of modules doesn't depend of this)
            supplier_price, = ProductSupplierPrice.create([{
                        'product_supplier': product_supplier.id,
                        'quantity': 0,
                        'unit_price': Decimal(16),
                        'discount': Decimal('0.20'),
                        }])
            self.assertEqual(supplier_price.gross_unit_price, Decimal(20))

            # Create supplier price defining gros_unit price
            supplier_price, = ProductSupplierPrice.create([{
                        'product_supplier': product_supplier.id,
                        'quantity': 0,
                        'gross_unit_price': Decimal(16),
                        'discount': Decimal('0.50'),
                        }])
            self.assertEqual(supplier_price.unit_price, Decimal(8))

            # Change gross unit price
            supplier_price.gross_unit_price = Decimal(30)
            supplier_price.update_prices()
            self.assertEqual(supplier_price.unit_price, Decimal(15))

            # Change gross unit price
            supplier_price.discount = Decimal('0.25')
            supplier_price.update_prices()
            self.assertEqual(supplier_price.unit_price, Decimal('22.5'))

            supplier_price.discount = Decimal('0')
            supplier_price.update_prices()
            self.assertEqual(supplier_price.unit_price, Decimal(30))

    @with_transaction()
    def test_purchase_price(self):
        'Test update price'
        pool = Pool()
        ProductSupplierPrice = pool.get('purchase.product_supplier.price')
        Purchase = pool.get('purchase.purchase')
        PurchaseLine = pool.get('purchase.line')

        company = create_company()
        with set_company(company):
            create_chart(company)
            supplier, product_supplier = create_supplier(company)

            ProductSupplierPrice.create([{
                'product_supplier': product_supplier.id,
                'quantity': 0,
                'unit_price': Decimal(16),
                }, {
                'product_supplier': product_supplier.id,
                'quantity': 5,
                'unit_price': Decimal(14),
                'discount': Decimal('0.10'),
                }, {
                'product_supplier': product_supplier.id,
                'quantity': 10,
                'unit_price': Decimal(12),
                'discount': Decimal('0.20'),
                }])

            purchase = Purchase()
            purchase.party = supplier
            purchase.currency = company.currency

            line1 = PurchaseLine()
            line1.purchase = purchase
            line1.product = product_supplier.id
            line1.quantity = 1
            line1.on_change_product()
            self.assertEqual(line1.unit_price, Decimal(16))
            self.assertEqual(line1.discount, 0)

            line2 = PurchaseLine()
            line2.purchase = purchase
            line2.product = product_supplier.id
            line2.quantity = 6
            line2.on_change_product()
            self.assertEqual(line2.unit_price, Decimal(14))
            self.assertEqual(line2.discount, Decimal('0.10'))

            line3 = PurchaseLine()
            line3.purchase = purchase
            line3.product = product_supplier.id
            line3.quantity = 20
            line3.on_change_product()
            self.assertEqual(line3.unit_price, Decimal(12))
            self.assertEqual(line3.discount, Decimal('0.20'))

def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        PurchaseSupplierDiscountTestCase))
    return suite
