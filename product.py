# This file is part of dish_recipe_product module.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'
    recipe = fields.One2Many('dish_recipe.recipe',
        'product', 'Recipe', readonly=True)
