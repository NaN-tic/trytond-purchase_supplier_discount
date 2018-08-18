# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

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

        gross_unit_price = gross_unit_price_wo_round = self.gross_unit_price
        unit_price = self.gross_unit_price
        discount = Decimal(0)

        with Transaction().set_context(self._get_context_purchase_price()):
            pattern = ProductSupplier.get_pattern()
            for product_supplier in self.product.product_suppliers:
                if product_supplier.match(pattern):
                    pattern = ProductSupplierPrice.get_pattern()
                    for price in product_supplier.prices:
                        if price.match(self.quantity, uom, pattern):
                            discount = price.discount or Decimal(0)
                            gross_unit_price_wo_round = price.gross_unit_price
                            unit_price = price.unit_price
                            break
                    break

        digits = self.__class__.unit_price.digits[1]
        unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

        digits = self.__class__.gross_unit_price.digits[1]
        gross_unit_price = gross_unit_price_wo_round.quantize(
            Decimal(str(10.0 ** -digits)))

        self.gross_unit_price = gross_unit_price
        self.gross_unit_price_wo_round = gross_unit_price_wo_round
        self.unit_price = unit_price
        self.discount = discount

    @fields.depends('product', 'discount')
    def on_change_quantity(self):
        super(PurchaseLine, self).on_change_quantity()

        if self.quantity and self.product:
            self.get_discount()

    @fields.depends('product', 'discount')
    def on_change_product(self):
        super(PurchaseLine, self).on_change_product()

        if self.quantity and self.product:
            self.get_discount()
