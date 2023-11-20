# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.modules.product import round_price

__all__ = ['PurchaseLine']


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    def get_discount(self):
        pool = Pool()
        Uom = pool.get('product.uom')
        ProductSupplier = pool.get('purchase.product_supplier')
        ProductSupplierPrice = pool.get('purchase.product_supplier.price')

        context = Transaction().context

        if context.get('uom'):
            uom = Uom(context['uom'])
        else:
            uom = self.product.default_uom

        gross_unit_price = self.gross_unit_price
        unit_price = self.gross_unit_price
        discount = Decimal(0)

        with Transaction().set_context(self._get_context_purchase_price()):
            pattern = ProductSupplier.get_pattern()
            for product_supplier in self.product.product_suppliers_used():
                if product_supplier.match(pattern):
                    pattern = ProductSupplierPrice.get_pattern()
                    for price in product_supplier.prices:
                        if price.match(self.quantity, uom, pattern):
                            discount = price.discount or Decimal(0)
                            gross_unit_price = price.gross_unit_price
                            unit_price = price.unit_price
                            break
                    break

        gup_digits = self.__class__.gross_unit_price.digits[1]
        gross_unit_price = gross_unit_price.quantize(
            Decimal(str(10.0 ** -gup_digits)))
        unit_price = round_price(unit_price)

        self.gross_unit_price = gross_unit_price
        self.unit_price = unit_price
        self.discount = discount

    @fields.depends('discount')
    def on_change_quantity(self):
        super(PurchaseLine, self).on_change_quantity()

        if self.quantity and self.product:
            self.get_discount()

    @fields.depends('quantity', 'discount')
    def on_change_product(self):
        super(PurchaseLine, self).on_change_product()

        if self.quantity and self.product:
            self.get_discount()
