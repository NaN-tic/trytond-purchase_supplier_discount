# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .product import *
from .purchase import *
from .purchase_request import *

def register():
    Pool.register(
        ProductSupplierPrice,
        PurchaseLine,
        module='purchase_supplier_discount', type_='model')
    Pool.register(
        CreatePurchase,
        module='purchase_supplier_discount', type_='wizard')
