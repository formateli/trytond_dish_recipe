# This file is part of Tryton. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.dish_recipe.tests.test_dish_recipe import suite
except ImportError:
    from .test_dish_recipe import suite


__all__ = ['suite']
