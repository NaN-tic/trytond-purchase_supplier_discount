# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.product import price_digits, round_price
from trytond.modules.currency.fields import Monetary
from trytond.transaction import Transaction


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    def get_product_supplier(self):
        ProductSupplier = Pool().get('purchase.product_supplier')

        pattern = ProductSupplier.get_pattern()
        product_suppliers = self.product_suppliers_used(**pattern)
        try:
            return next(product_suppliers)
        except StopIteration:
            return None

    @classmethod
    def get_base_price(cls, products, quantity=0):
        '''
        This method resembles the get_purchase_price method from the purchase module.

        The context that can have as keys:
            uom: the unit of measure
            supplier: the supplier party id
            currency: the currency id for the returned price
        '''
        pool = Pool()
        Uom = pool.get('product.uom')
        Company = pool.get('company.company')
        Currency = pool.get('currency.currency')
        Date = pool.get('ir.date')

        context = Transaction().context
        prices = {}

        assert len(products) == len(set(products)), "Duplicate products"

        uom = None
        if context.get('uom'):
            uom = Uom(context['uom'])

        currency = None
        if context.get('currency'):
            currency = Currency(context['currency'])
        elif context.get('company'):
            currency = Company(context['company']).currency
        date = context.get('purchase_date') or Date.today()

        last_purchase_prices = cls.get_last_purchase_price_uom(products)

        for product in products:
            unit_price = product._get_purchase_unit_price(quantity=quantity)
            default_uom = product.default_uom
            default_currency = currency
            if not uom or default_uom.category != uom.category:
                product_uom = default_uom
            else:
                product_uom = uom
            product_supplier = product.get_product_supplier()
            if product_supplier:
                price = product_supplier.get_price(quantity, product_uom)
                if price:
                    unit_price = price.base_price
                    default_uom = product_supplier.unit
                    default_currency = product_supplier.currency
                if unit_price is not None:
                    unit_price = Uom.compute_price(
                        default_uom, unit_price, product_uom)
                    if currency and default_currency:
                        with Transaction().set_context(date=date):
                            unit_price = Currency.compute(
                                default_currency, unit_price, currency,
                                round=False)
            if unit_price is None:
                unit_price = last_purchase_prices[product.id]
            else:
                unit_price = round_price(unit_price)
            prices[product.id] = unit_price
        return prices


class ProductSupplier(metaclass=PoolMeta):
    __name__ = 'purchase.product_supplier'

    def get_price(self, quantity, product_uom):
        SupplierPrice = Pool().get('purchase.product_supplier.price')

        pattern = SupplierPrice.get_pattern()
        for price in self.prices:
            if price.match(quantity, product_uom, pattern):
                return price
        return None


class ProductSupplierPrice(metaclass=PoolMeta):
    __name__ = 'purchase.product_supplier.price'
    base_price = Monetary(
        "Base Price", currency='currency', digits=price_digits)

    discount_rate = fields.Function(fields.Numeric(
            "Discount Rate", digits=(16, 4)),
        'on_change_with_discount_rate', setter='set_discount_rate')
    discount_amount = fields.Function(Monetary(
            "Discount Amount", currency='currency', digits=price_digits),
        'on_change_with_discount_amount', setter='set_discount_amount')

    discount = fields.Function(fields.Char(
            "Discount",
            states={
                'invisible': ~Eval('discount'),
                }),
        'on_change_with_discount')

    @classmethod
    def __register__(cls, module_name):
        # Rename gross_unit_price to base_price
        table = cls.__table_handler__(module_name)
        if table.column_exist('gross_unit_price') and not table.column_exist('base_price'):
            table.column_rename('gross_unit_price', 'base_price')
        super().__register__(module_name)

    @fields.depends('unit_price', 'base_price')
    def on_change_with_discount_rate(self, name=None):
        if self.unit_price is None or not self.base_price:
            return
        rate = 1 - self.unit_price / self.base_price
        return rate.quantize(
            Decimal(1) / 10 ** self.__class__.discount_rate.digits[1])

    @fields.depends(
        'base_price', 'discount_rate',
        methods=['on_change_with_discount_amount', 'on_change_with_discount'])
    def on_change_discount_rate(self):
        if self.base_price is not None and self.discount_rate is not None:
            self.unit_price = round_price(
                self.base_price * (1 - self.discount_rate))
            self.discount_amount = self.on_change_with_discount_amount()
            self.discount = self.on_change_with_discount()

    @classmethod
    def set_discount_rate(cls, lines, name, value):
        pass

    @fields.depends('unit_price', 'base_price')
    def on_change_with_discount_amount(self, name=None):
        if self.unit_price is None or self.base_price is None:
            return
        return round_price(self.base_price - self.unit_price)

    @fields.depends(
        'base_price', 'discount_amount',
        methods=['on_change_with_discount_rate', 'on_change_with_discount'])
    def on_change_discount_amount(self):
        if self.base_price is not None and self.discount_amount is not None:
            self.unit_price = round_price(
                self.base_price - self.discount_amount)
            self.discount_rate = self.on_change_with_discount_rate()
            self.discount = self.on_change_with_discount()

    @classmethod
    def set_discount_amount(cls, lines, name, value):
        pass

    @fields.depends('product_supplier', 'currency', '_parent_product_supplier.currency',
        methods=[
            'on_change_with_discount_rate', 'on_change_with_discount_amount'])
    def on_change_with_discount(self, name=None):
        pool = Pool()
        Lang = pool.get('ir.lang')
        Company = pool.get('company.company')

        lang = Lang.get()
        rate = self.on_change_with_discount_rate()
        if not rate or rate % Decimal('0.01'):
            amount = self.on_change_with_discount_amount()
            if amount is not None:
                currency = self.currency
                if not currency:
                    company = Company(Transaction().context['company'])
                    currency = company.currency
                if currency:
                    return lang.currency(
                        amount, currency, digits=price_digits[1])
                else:
                    return f"{amount}"
        else:
            return lang.format('%i', rate * 100) + '%'
