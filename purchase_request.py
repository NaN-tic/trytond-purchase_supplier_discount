# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['CreatePurchase']
__metaclass__ = PoolMeta


class CreatePurchase:
    __name__ = 'purchase.request.create_purchase'

    @classmethod
    def compute_purchase_line(cls, request, purchase):
        line = super(CreatePurchase, cls).compute_purchase_line(request,
            purchase)

        line.purchase = purchase # The pattern to match price is from a purchase
        line.on_change_quantity() # get discount and gross/unit price

        return line
