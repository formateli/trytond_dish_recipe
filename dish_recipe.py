#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, If
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.product import price_digits
from decimal import Decimal

__all__ = [
        'Recipe',
        'SubRecipe',
        'RecipePrice',
        'RecipeComponent',
    ]


class Recipe(ModelSQL, ModelView, CompanyMultiValueMixin):
    'Dish Recipe'
    __name__ = 'dish_recipe.recipe'

    name = fields.Char('Name', required=True, translate=True)
    description = fields.Char('Brief Description', size=None)
    preparation = fields.Text('Preparation')
    product = fields.Many2One('product.product', 'Product associated',
        help='Product associated with this recipe. It must ' 
            'be "Service" type and "Unit" unit.',
        domain=[
            ('type', '=', 'service'),
            ('template.default_uom', '=', Eval('unit')),
        ], depends=['unit'])
    unit = fields.Function(fields.Many2One('product.uom', 'Unit'),
        'get_unit')
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
            ('subrecipe.id', '!=', Eval('id')),
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
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost')
    total_cost = fields.Function(fields.Numeric('Total',
            digits=price_digits),
        'get_total_cost')

    @fields.depends('unit')
    def on_change_with_unit_digits(self, name=None):
        if self.unit:
            return self.unit.digits
        return 2

    @fields.depends('product')
    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id

    def get_cost(self, name=None):
        Uom = Pool().get('product.uom')
        if not self.product or not self.unit:
            return Decimal('0.0')
        cost = Uom.compute_price(
            self.product.default_uom,
            self.product.cost_price,
            self.unit)
        return cost

    def get_total_cost(self, name=None):
        if not self.quantity:
            return Decimal('0.0')
        return self.cost * Decimal(self.quantity)

    @fields.depends('product', 'unit', 'quantity')
    def on_change_quantity(self):
        self.cost = self.get_cost()
        self.total_cost = self.get_total_cost()

    @fields.depends(methods=['on_change_quantity'])
    def on_change_unit(self):
        self.on_change_quantity()
