# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    @fields.depends('product', 'quantity', 'base_price',
        methods=['_get_context_purchase_price'])
    def compute_base_price(self):
        pool = Pool()
        Product = pool.get('product.product')

        base_price = super().compute_base_price()
        if self.product:
            with Transaction().set_context(self._get_context_purchase_price()):
                base_price = Product.get_base_price(
                    [self.product], abs(self.quantity or 0))[self.product.id]
        if base_price is None:
            base_price = self.base_price
        return base_price

