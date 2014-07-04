#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import doctest
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view,\
    test_depends
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    'Test module'

    def setUp(self):
        trytond.tests.test_tryton.install_module(
            'purchase_supplier_discount')
        self.uom = POOL.get('product.uom')
        self.uom_category = POOL.get('product.uom.category')
        self.category = POOL.get('product.category')
        self.template = POOL.get('product.template')
        self.product = POOL.get('product.product')
        self.company = POOL.get('company.company')
        self.party = POOL.get('party.party')
        self.account = POOL.get('account.account')
        self.product_supplier = POOL.get('purchase.product_supplier')
        self.supplier_price = POOL.get('purchase.product_supplier.price')
        self.user = POOL.get('res.user')

    def test0005views(self):
        'Test views'
        test_view('purchase_supplier_discount')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def test0010update_prices(self):
        '''
        Test price computation in create() and update_prices() Product methods
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin'),
                    ])
            self.user.write([self.user(USER)], {
                'main_company': company.id,
                'company': company.id,
                })

            # Prepare product
            uom_category, = self.uom_category.create([{'name': 'Test'}])
            uom, = self.uom.create([{
                        'name': 'Test',
                        'symbol': 'T',
                        'category': uom_category.id,
                        'rate': 1.0,
                        'factor': 1.0,
                        }])
            category, = self.category.create([{'name': 'ProdCategoryTest'}])
            template, = self.template.create([{
                        'name': 'ProductTest',
                        'default_uom': uom.id,
                        'category': category.id,
                        'account_category': True,
                        'list_price': Decimal(0),
                        'cost_price': Decimal(10),
                        }])
            self.product.create([{
                        'template': template.id,
                        }])

            # Prepare supplier
            receivable, = self.account.search([
                ('kind', '=', 'receivable'),
                ('company', '=', company.id),
                ])
            payable, = self.account.search([
                ('kind', '=', 'payable'),
                ('company', '=', company.id),
                ])
            supplier, = self.party.create([{
                        'name': 'supplier',
                        'account_receivable': receivable.id,
                        'account_payable': payable.id,
                        }])

            # Prepare product supplier
            product_supplier, = self.product_supplier.create([{
                        'product': template.id,
                        'company': company.id,
                        'party': supplier.id,
                        'delivery_time': 2,
                        }])

            # Create supplier price defining unit price and not gross unit
            # price (support of modules doesn't depend of this)
            supplier_price, = self.supplier_price.create([{
                        'product_supplier': product_supplier.id,
                        'quantity': 0,
                        'unit_price': Decimal(16),
                        'discount': Decimal('0.20'),
                        }])
            self.assertEqual(supplier_price.gross_unit_price, Decimal(20))

            # Create supplier price defining gros_unit price
            supplier_price, = self.supplier_price.create([{
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


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    for test in test_company.suite():
        if test not in suite:
            suite.addTest(test)
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        if test not in suite and not isinstance(test, doctest.DocTestCase):
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
