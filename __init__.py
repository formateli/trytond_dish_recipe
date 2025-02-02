#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import dish_recipe
from . import category
from . import product


def register():
    Pool.register(
        dish_recipe.Recipe,
        dish_recipe.SubRecipe,
        dish_recipe.RecipePrice,
        dish_recipe.RecipePublish,
        dish_recipe.RecipeComponent,
        category.Category,
        product.Product,
        module='dish_recipe', type_='model')
