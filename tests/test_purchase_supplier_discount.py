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
    Category = pool.get('product.category')
    Template = pool.get('product.template')
    Uom = pool.get('product.uom')
    ProductSupplier = pool.get('purchase.product_supplier')
    Party = pool.get('party.party')

    revenue, = Account.search([
                ('type.revenue', '=', True),
                ('company', '=', company.id),
                ])
    expense, = Account.search([
                ('type.expense', '=', True),
                ('company', '=', company.id),
                ])

    account_category, = Category.create([{
                'name': 'Category',
                'accounting': True,
                'account_revenue': revenue.id,
                'account_expense': expense.id,
                }])

    u, = Uom.search([('name', '=', 'Unit')])
    template, = Template.create([{
                'name': 'Product',
                'account_category': account_category.id,
                'default_uom': u.id,
                'purchase_uom': u.id,
                'list_price': Decimal(0),
                'products': [('create', [{}])],
                }])
    product, = template.products
    product.cost_price = Decimal(10)
    product.save()

    # Prepare supplier
    receivable, = Account.search([
                ('type.receivable', '=', True),
                ('company', '=', company.id),
                ])
    payable, = Account.search([
                ('type.payable', '=', True),
                ('company', '=', company.id),
                ])
    supplier1, supplier2, = Party.create([{
                'name': 'Supplier 1',
                'account_receivable': receivable.id,
                'account_payable': payable.id,
                }, {
                'name': 'Supplier 2',
                'account_receivable': receivable.id,
                'account_payable': payable.id,
                }])

    # Prepare product supplier
    product_supplier1, product_supplier2 = ProductSupplier.create([{
                'template': template.id,
                'product': product.id,
                'company': company.id,
                'party': supplier1.id,
                'lead_time': datetime.timedelta(days=2),
                }, {
                'template': template.id,
                'product': product.id,
                'company': company.id,
                'party': supplier2.id,
                'lead_time': datetime.timedelta(days=2),
                }])
    return supplier1, supplier2, product, product_supplier1, product_supplier2


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
            _, _, _, product_supplier1, _ = create_supplier(company)

            # Create supplier price defining unit price and not gross unit
            # price (support of modules doesn't depend of this)
            supplier_price, = ProductSupplierPrice.create([{
                        'product_supplier': product_supplier1.id,
                        'quantity': 0,
                        'unit_price': Decimal(16),
                        'discount': Decimal('0.20'),
                        }])
            self.assertEqual(supplier_price.gross_unit_price, Decimal(20))

            # Create supplier price defining gros_unit price
            supplier_price, = ProductSupplierPrice.create([{
                        'product_supplier': product_supplier1.id,
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
            supplier1, _, product, product_supplier1, _ = (
                create_supplier(company))

            ProductSupplierPrice.create([{
                'sequence': 1,
                'product_supplier': product_supplier1.id,
                'quantity': 10,
                'unit_price': Decimal(12),
                'discount': Decimal('0.20'),
                }, {
                'sequence': 2,
                'product_supplier': product_supplier1.id,
                'quantity': 5,
                'unit_price': Decimal(14),
                'discount': Decimal('0.10'),
                }, {
                'sequence': 3,
                'product_supplier': product_supplier1.id,
                'quantity': 0,
                'unit_price': Decimal(16),
                }])

            purchase = Purchase()
            purchase.party = supplier1
            purchase.currency = company.currency

            line1 = PurchaseLine()
            line1.purchase = purchase
            line1.product = product
            line1.quantity = 1
            line1.on_change_product()
            self.assertEqual(line1.unit_price, Decimal(16))
            self.assertEqual(line1.discount, 0)

            line2 = PurchaseLine()
            line2.purchase = purchase
            line2.product = product
            line2.quantity = 6
            line2.on_change_product()
            self.assertEqual(line2.unit_price, Decimal(14))
            self.assertEqual(line2.discount, Decimal('0.10'))

            line3 = PurchaseLine()
            line3.purchase = purchase
            line3.product = product
            line3.quantity = 20
            line3.on_change_product()
            self.assertEqual(line3.unit_price, Decimal(12))
            self.assertEqual(line3.discount, Decimal('0.20'))


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        PurchaseSupplierDiscountTestCase))
    return suite
