# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.config import config
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.modules.product import price_digits
DISCOUNT_DIGITS = int(config.get('digits', 'discount_digits', default=4))

__all__ = ['ProductSupplierPrice']


class ProductSupplierPrice:
    __name__ = 'purchase.product_supplier.price'
    __metaclass__ = PoolMeta
    gross_unit_price = fields.Numeric('Gross Price', digits=price_digits,
        required=True)
    discount = fields.Numeric('Discount', digits=(16, DISCOUNT_DIGITS))

    @classmethod
    def __setup__(cls):
        super(ProductSupplierPrice, cls).__setup__()
        cls.unit_price.states['readonly'] = True
        cls.unit_price.digits = (20, price_digits[1] + DISCOUNT_DIGITS)

    @fields.depends('gross_unit_price', 'discount')
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'discount')
    def on_change_discount(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'discount')
    def update_prices(self):
        unit_price = self.gross_unit_price
        gross_unit_price = self.gross_unit_price
        if self.gross_unit_price is not None and self.discount is not None:
            unit_price = self.gross_unit_price * (1 - self.discount)
            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

            if self.discount != 1:
                gross_unit_price = unit_price / (1 - self.discount)
            digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price.quantize(
                Decimal(str(10.0 ** -digits)))
        self.gross_unit_price = gross_unit_price
        self.unit_price = unit_price

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            if not vals.get('gross_unit_price'):
                gross_unit_price = vals.get('unit_price', Decimal('0.0'))
                if 'discount' in vals and vals['discount'] != 1:
                    gross_unit_price = gross_unit_price / (1 - vals['discount'])
                    digits = cls.gross_unit_price.digits[1]
                    gross_unit_price = gross_unit_price.quantize(
                        Decimal(str(10.0 ** -digits)))
                vals['gross_unit_price'] = gross_unit_price
            elif not vals.get('unit_price'):
                unit_price = vals.get('gross_unit_price', Decimal('0.0'))
                if 'discount' in vals and vals['discount'] != 1:
                    supplier_price = cls()
                    supplier_price.gross_unit_price = unit_price
                    supplier_price.discount = vals['discount']
                    unit_price = supplier_price.update_prices()['unit_price']
                vals['unit_price'] = unit_price
            if 'discount' not in vals:
                vals['discount'] = Decimal(0)
        return super(ProductSupplierPrice, cls).create(vlist)
