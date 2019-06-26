# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields, tree

__all__ = ['Category']


class Category(tree(separator=' / '), ModelSQL, ModelView):
    "Recipe Category"
    __name__ = "dish_recipe.category"
    name = fields.Char('Name', required=True, translate=True)
    parent = fields.Many2One('dish_recipe.category', 'Parent', select=True)
    childs = fields.One2Many('dish_recipe.category', 'parent',
            string='Children')
    recipes = fields.One2Many('dish_recipe.recipe',
            'category', 'Recipes')

    @classmethod
    def __setup__(cls):
        super(Category, cls).__setup__()
        cls._order.insert(0, ('name', 'ASC'))
