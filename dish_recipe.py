#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, If
from decimal import Decimal

__all__ = [
        'Recipe',
        'RecipeComponent',
        'RecipeAttachment,'
        'RecipeCostPrice'
    ]


class Recipe(ModelSQL, ModelView):
    'Dish Recipe'
    __name__ = 'dish_recipe.recipe'

    company = fields.Function(fields.Many2One('company.company', 'Company'),
        'get_company')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'get_currency_digits')
    product = fields.Many2One('product.product', 'Product',
        required=True,
        domain=[('type', '=', 'service')],
        states={
            'readonly': Bool(Eval('components')),
        }, depends=['components'])
    components = fields.One2Many('dish_recipe.recipe.component',
        'recipe', 'Components',
        domain=[
            ('product', '!=', Eval('product')),
        ], depends=['product'])
    decription = fields.Text('Description')
    cost_price = fields.One2Many('dish_recipe.recipe.cost_price',
        'recipe', 'Cost/Price',
        domain=[
            ('company', '=', Eval('company'))
        ], depends=['company'])
    attachments = fields.One2Many('dish_recipe.recipe.attachment',
        'recipe', 'Attachments')
    cost = fields.Function(fields.Numeric('Cost',
            digits=(16, Eval('currency_digits',2)),
            depends=['currency_digits']),
        'get_num_value')
    price = fields.Function(fields.Numeric('Price',
            digits=(16, Eval('currency_digits',2)),
            depends=['currency_digits']),
        'get_num_value')
    percentage = fields.Function(fields.Numeric('Percentage',
            digits=(16, Eval('currency_digits',2)),
            depends=['currency_digits']),
        'get_num_value')

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    def get_company(self, name=None):
        return Transaction().context.get('company')

    def get_num_value(self, name=None):
        CostPrice = Pool().get('dish_recipe.recipe.cost_price')
        result = Decimal('0.0')
        
        cost_price = CostPrice.search([
                ('company', '=', self.company.id),            
            ], limit=1)

        if cost_price:
            cp = cost_price[0]
            if name == 'cost':
                result = cp.cost
            if name == 'price':
                result = cp.price
            if name == 'percentage':
                result = cp.percentage

        return result

    def get_currency_digits(self, name=None):
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            company = Company(company)
            return company.currency.digits
        return 2


class RecipeComponent(ModelSQL, ModelView):
    'Purchase Line'
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
                ('category', '!=', -1)),
            ],
        depends=['product_uom_category'])
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'on_change_with_product_uom_category')

    @fields.depends('unit')
    def on_change_with_unit_digits(self, name=None):
        if self.unit:
            return self.unit.digits
        return 2

    @fields.depends('product')
    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id


class RecipeAttachment(ModelSQL, ModelView):
    'Recipe Attachment'
    __name__ = 'dish_recipe.recipe.attachment'

    recipe = fields.Many2One(
        'dish_recipe.recipe', 'Recipe', required=True)
    name = fields.Char('Name', required=True)
    description = fields.Text('Description', size=None)
    attachment = fields.Binary('Attachment', file_id='doc_id',
        required=True)
    doc_id = fields.Char('Doc id',
            states={'invisible': True}
        )


class RecipeCostPrice(ModelSQL, ModelView):
    'Recipe Cost/Price'
    __name__ = 'dish_recipe.recipe.cost_price'

    company = fields.Many2One('company.company', 'Company',
        select=True, required=True,
        states={
            'readonly': True,
            },
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ])
    recipe = fields.Many2One(
        'dish_recipe.recipe', 'Recipe', required=True)
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'get_currency_digits')
    date = fields.Date('Date', required=True)
    cost = fields.Numeric('Cost',
        digits=(16, Eval('currency_digits', 2)),
        states={
            'readonly': True,
        },
        depends=['currency_digits'])
    price = fields.Numeric('Price',
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'])
    percentage = fields.Function(fields.Numeric('Percentage',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'on_change_with_percentage')

    @classmethod
    def __setup__(cls):
        super(RecipeCostPrice, cls).__setup__()
        cls._order = [
                ('date', 'DESC'),
                ('id', 'DESC'),
            ]

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_date():
        pool = Pool()
        Date = pool.get('ir.date')
        return Date.today()

    @staticmethod
    def default_price():
        return Decimal('0.0')

    @staticmethod
    def default_cost():
        return Decimal('0.0')

    @staticmethod
    def default_currency_digits():
        return 2

    def get_currency_digits(self, name=None):
        if self.recipe:
            self.recipe.currency_digits
        return 2

    @fields.depends('cost', 'price')
    def on_change_with_percentage(self, name=None):
        res = Decimal('0.0')
        if self.price:
            res = self.cost / self.price
        return res

    def update_cost_price(self):
        Uom = Pool().get('product.uom')

        if self.recipe and self.recipe.components:
            result = Decimal('0.0')
            for component in self.recipe.components:
                quantity = Uom.compute_qty(
                    component.unit,
                    component.quantity,
                    component.product.default_uom)
                result += Decimal(quantity) * component.product.cost_price
                    
            self.cost = result

