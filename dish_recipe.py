#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, If
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.exceptions import UserError
from trytond.modules.product import price_digits
from decimal import Decimal

__all__ = [
        'Recipe',
        'RecipePrice',
        'RecipeComponent',
        'RecipeAttachment,'
    ]


class Recipe(ModelSQL, ModelView, CompanyMultiValueMixin):
    'Dish Recipe'
    __name__ = 'dish_recipe.recipe'

    product = fields.Many2One('product.product', 'Product',
        required=True,
        domain=[
            ('type', '=', 'service'),
            ('template.default_uom', '=', Eval('unit')),
        ],
        states={
            'readonly': Bool(Eval('components')),
        }, depends=['components', 'unit'])
    unit = fields.Function(fields.Many2One('product.uom', 'Unit'),
        'get_unit')
    components = fields.One2Many('dish_recipe.recipe.component',
        'recipe', 'Components',
        domain=[
            ('product', '!=', Eval('product')),
        ], depends=['product'])
    description = fields.Char('Brief Description', size=None)
    preparation = fields.Text('Preparation')
    attachments = fields.One2Many('dish_recipe.recipe.attachment',
        'recipe', 'Attachments')
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost')
    price = fields.MultiValue(fields.Numeric('Price', required=True,
            digits=price_digits))
    prices = fields.One2Many(
        'dish_recipe.price', 'recipe', 'Prices')
    percentage = fields.Function(fields.Numeric('Percentage',
            digits=price_digits),
        'get_percentage')

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'price':
            return pool.get('dish_recipe.price')
        return super(Recipe, cls).multivalue_model(field)

    def get_unit(self, name=None):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        uom_id = ModelData.get_id('product', 'uom_unit')
        return uom_id

    def get_cost(self, name=None):
        Uom = Pool().get('product.uom')
        if not self.components:
            return
        result = Decimal('0.0')
        for component in self.components:
            if component.product.recipe:
                if not component.product.recipe[0].cost:
                    continue
                result += component.product.recipe[0].cost
            else:
                if not component.product.cost_price:
                    continue
                quantity = Uom.compute_qty(
                    component.unit,
                    component.quantity,
                    component.product.default_uom)
                result += Decimal(quantity) * component.product.cost_price
        return result

    def get_percentage(self, name=None):
        if self.price is None or self.cost is None:
            return
        result = self.cost / self.price * Decimal('100.0')
        return result

    @classmethod
    def validate(cls, recipes):
        Rcp = Pool().get('dish_recipe.recipe')
        for recipe in recipes:
            rcp = Rcp.search([
                    ('product', '=', recipe.product.id),
                    ('id', '!=', recipe.id),
                ])
            if rcp:
                raise UserError(
                    gettext('dish_recipe.msg_product_selected',
                        product=product.rec_name,
                        recipe=recipe.rec_name,
                        rcp=rcp.rec_name))


class RecipePrice(ModelSQL, CompanyValueMixin):
    "Recipe Price"
    __name__ = 'dish_recipe.price'
    recipe = fields.Many2One(
        'dish_recipe.recipe', 'Recipe', ondelete='CASCADE', select=True)
    price = fields.Numeric("Price", digits=price_digits)


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
