#This file is part of tryton-rrhh project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import dish_recipe


def register():
    Pool.register(
        dish_recipe.Recipe,
        dish_recipe.RecipeComponent,
        dish_recipe.RecipeAttachment,
        dish_recipe.RecipeCostPrice,
        module='dish_recipe', type_='model')
