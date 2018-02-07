# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import product
from . import purchase


def register():
    Pool.register(
        product.ProductSupplierPrice,
        purchase.PurchaseLine,
        module='purchase_supplier_discount', type_='model')
