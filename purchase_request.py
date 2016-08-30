# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta

__all__ = ['CreatePurchase']
__metaclass__ = PoolMeta


class CreatePurchase:
    __name__ = 'purchase.request.create_purchase'

    @classmethod
    def compute_purchase_line(cls, key, requests, purchase):
        line = super(CreatePurchase, cls).compute_purchase_line(key, requests,
            purchase)
        line.purchase = purchase # The pattern to match price is from a purchase
        # get discount and gross/unit price
        for key, value in line.on_change_quantity().iteritems():
            setattr(line, key, value)
        return line
