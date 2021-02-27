#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, If
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.modules.product import price_digits
from trytond.modules.account.tax import _TaxKey
from decimal import Decimal


class Recipe(ModelSQL, ModelView, CompanyMultiValueMixin):
    'Dish Recipe'
    __name__ = 'dish_recipe.recipe'
    name = fields.Char('Name', required=True, translate=True)
    description = fields.Char('Brief Description', size=None)
    preparation = fields.Text('Preparation')
    category = fields.Many2One('dish_recipe.category',
        'Category', required=True)
    components = fields.One2Many('dish_recipe.recipe.component',
        'recipe', 'Components',
        domain=[
            ('product', '!=', Eval('product')),
        ], depends=['product'])
    subrecipes = fields.One2Many('dish_recipe.recipe.subrecipe',
        'recipe', 'Sub Recipe',
        domain=[
            ('id', '!=', Eval('id')),
        ], depends=['id'])
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    cost_components = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost_components')
    cost_subrecipes = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost_subrecipes')
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost')
    price = fields.MultiValue(fields.Numeric('Price',
            digits=price_digits))
    prices = fields.One2Many(
        'dish_recipe.price', 'recipe', 'Prices')
    percentage = fields.Function(fields.Numeric('Percentage',
            digits=price_digits),
        'get_percentage')
    product = fields.Many2One('product.product', 'Product associated',
        help='Product associated with this recipe.')
    active = fields.Boolean('Active')

    @classmethod
    def __register__(cls, module_name):
        super(Recipe, cls).__register__(module_name)
        table = cls.__table_handler__(module_name)
        # Migration from 5.8.0:
        if table.column_exist('quantity'):
            table.drop_column('quantity')
            table.drop_column('unit')

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'price':
            return pool.get('dish_recipe.price')
        return super(Recipe, cls).multivalue_model(field)

    @staticmethod
    def default_active():
        return True

    def get_cost_components(self, name=None):
        result = Decimal('0.0')
        for component in self.components:
            if component.total_cost:
                result += component.total_cost
        exp = Decimal(str(10.0 ** -price_digits[1]))
        return result.quantize(exp)

    def get_cost_subrecipes(self, name=None):
        result = Decimal('0.0')
        for recipe in self.subrecipes:
            if recipe.total_cost:
                result += recipe.total_cost
        exp = Decimal(str(10.0 ** -price_digits[1]))
        return result.quantize(exp)

    def get_cost(self, name=None):
        return self.cost_components + self.cost_subrecipes

    def get_percentage(self, name=None):
        if self.price is None or self.cost is None:
            return
        result = self.cost / self.price * Decimal('100.0')
        exp = Decimal(str(10.0 ** -price_digits[1]))
        return result.quantize(exp)

    @fields.depends('cost', 'percentage',
        'components', 'subrecipes', 'price')
    def on_change_price(self):
        self.cost_components = self.get_cost_components()
        self.cost_subrecipes = self.get_cost_subrecipes()
        self.cost = self.get_cost()
        self.percentage = self.get_percentage()

    @fields.depends(methods=['on_change_price'])
    def on_change_components(self):
        self.on_change_price()

    @fields.depends(methods=['on_change_price'])
    def on_change_subrecipes(self):
        self.on_change_price()

    @classmethod
    def delete(cls, recipes):
        Attachment = Pool().get('ir.attachment')
        attachments = [a for h in recipes for a in h.attachments]
        Attachment.delete(attachments)
        super(Recipe, cls).delete(recipes)

    @classmethod
    def copy(cls, recipes, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['attachments'] = None
        return super(Recipe, cls).copy(recipes, default=default)

    @classmethod
    def validate(cls, recipes):
        for recipe in recipes:
            if recipe.product:
                rcp = cls.search([
                        ('product', '=', recipe.product.id),
                        ('id', '!=', recipe.id),
                    ])
                if rcp:
                    raise UserError(
                        gettext('dish_recipe_product.msg_product_selected',
                            product=product.rec_name,
                            recipe=recipe.rec_name,
                            rcp=rcp.rec_name))
        super(Recipe, cls).validate(recipes)


class RecipePrice(ModelSQL, CompanyValueMixin):
    "Recipe Price"
    __name__ = 'dish_recipe.price'
    recipe = fields.Many2One(
        'dish_recipe.recipe', 'Recipe', ondelete='CASCADE', select=True)
    price = fields.Numeric("Price", digits=price_digits)


class SubRecipe(ModelSQL, ModelView):
    'Sub Recipe'
    __name__ = 'dish_recipe.recipe.subrecipe'

    recipe = fields.Many2One('dish_recipe.recipe', 'Recipe',
        ondelete='CASCADE', select=True, required=True)
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'get_unit_digits')
    subrecipe = fields.Many2One('dish_recipe.recipe', 'Recipe', required=True,
        domain=[
            ('id', '!=', Eval(
                '_parent_recipe', {}).get(
                'id', -1))
        ])
    quantity = fields.Float('Quantity', required=True,
        digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'])
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost')
    total_cost = fields.Function(fields.Numeric('Total',
            digits=price_digits),
        'get_total_cost')

    def get_unit_digits(self, name=None):
        return price_digits[1]

    def get_cost(self, name=None):
        if not self.subrecipe:
            return Decimal('0.0')
        return self.subrecipe.cost

    def get_total_cost(self, name=None):
        if not self.quantity:
            return Decimal('0.0')
        return self.cost * Decimal(self.quantity)

    @fields.depends('quantity', 'subrecipe')
    def on_change_subrecipe(self):
        self.cost = self.get_cost()
        self.total_cost = self.get_total_cost()

    @fields.depends(methods=['on_change_subrecipe'])
    def on_change_quantity(self):
        self.on_change_subrecipe()


class RecipeComponent(ModelSQL, ModelView):
    'Recipe Component'
    __name__ = 'dish_recipe.recipe.component'

    recipe = fields.Many2One('dish_recipe.recipe', 'Recipe',
        ondelete='CASCADE', select=True, required=True)
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    product = fields.Many2One('product.product', 'Product', required=True,
        domain=[
            ('id', '!=', Eval(
                '_parent_recipe', {}).get(
                'product', -1))
        ])
    quantity = fields.Float('Quantity', required=True,
        digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'])
    unit = fields.Many2One('product.uom', 'Unit', required=True,
        domain=[
            If(Bool(Eval('product_uom_category')),
                ('category', '=', Eval('product_uom_category')),
                ('category', '=', -1)),
            ],
        depends=['product_uom_category'])
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'on_change_with_product_uom_category')
    waste = fields.Float('Waste Percentage', digits=price_digits)
    taxes = fields.Boolean('Include taxes')
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'on_change_with_cost')
    total_cost = fields.Function(fields.Numeric('Total',
            digits=price_digits),
        'on_change_with_total_cost')

    @fields.depends('unit')
    def on_change_with_unit_digits(self, name=None):
        if self.unit:
            return self.unit.digits
        return 2

    @fields.depends('product')
    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id

    @fields.depends('product', 'unit', 'taxes')
    def on_change_with_cost(self, name=None):
        return self._calculate_cost(self.product, self.unit, self.taxes)

    @fields.depends('quantity', 'cost', 'waste', 'taxes')
    def on_change_with_total_cost(self, name=None):
        if not self.quantity:
            return Decimal('0.0')
        total = self.cost * Decimal(self.quantity)
        if self.waste and (self.waste > 0 and self.waste < 100):
            waste = total * Decimal((self.waste / 100))
            total += waste
        return total

    def _calculate_cost(self, product, unit, include_tax):
        if not product or not unit:
            return Decimal('0.0')
        Uom = Pool().get('product.uom')
        cost = Uom.compute_price(
            product.default_uom,
            product.cost_price,
            unit)

        res = cost
        if include_tax:
            tax_amount = self._compute_taxes(product, cost)
            res = cost + tax_amount
        return res

    def _compute_taxes(self, product, cost):
        pool = Pool()
        Tax = pool.get('account.tax')
        Company = pool.get('company.company')

        tax_ids = []
        taxes = {}
        currency = None

        company_id = Transaction().context.get('company', None)
        if company_id is not None:
            currency = Company(company_id).currency

        print(product.name)

        for tax in product.supplier_taxes_used:
            tax_ids.append(tax.id)

        l_taxes = Tax.compute(Tax.browse(tax_ids), cost, 1, None)
        #print(l_taxes)

        for tax in l_taxes:
            taxline = self._compute_tax_line(**tax)
            # Base must always be rounded per line as there will be one
            # tax line per taxable_lines
            if currency is not None:
                taxline['base'] = currency.round(taxline['base'])
            if taxline not in taxes:
                taxes[taxline] = taxline
            else:
                taxes[taxline]['base'] += taxline['base']
                taxes[taxline]['amount'] += taxline['amount']

        self._round_taxes(taxes, currency)
        res = Decimal('0.0')
        for tx in taxes.items():
            res = tx[0]['amount']
        return res

    @staticmethod
    def _compute_tax_line(amount, base, tax):
        if base >= 0:
            type_ = 'invoice'
        else:
            type_ = 'credit_note'

        line = {}
        line['manual'] = False
        line['description'] = tax.description
        line['legal_notice'] = tax.legal_notice
        line['base'] = base
        line['amount'] = amount
        line['tax'] = tax.id
        line['account'] = getattr(tax, '%s_account' % type_).id

        return _TaxKey(**line)

    @staticmethod
    def _round_taxes(taxes, currency):
        if not currency:
            return
        for taxline in taxes.values():
            taxline['amount'] = currency.round(taxline['amount'])
