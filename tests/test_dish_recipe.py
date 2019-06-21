# This file is part of tryton-corseg module. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import unittest
import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.modules.company.tests import create_company, set_company
from trytond.exceptions import UserError
from decimal import Decimal


class DishRecipeTestCase(ModuleTestCase):
    'Test Dish Recipe module'
    module = 'dish_recipe'

    @with_transaction()
    def test_product_is_service(self):
        pool = Pool()
        Recipe = pool.get('dish_recipe.recipe')
        transaction = Transaction()
        product_1 = self._create_product('product_1', 'Kilogram')
        # product must be a service
        self.assertRaises(Exception, Recipe.create, [{
                'product': product_1.id,
                }]
            )
        transaction.rollback()

    @with_transaction()
    def test_dish_recipe(self):
        pool = Pool()
        Recipe = pool.get('dish_recipe.recipe')
        RecipeAttachment = pool.get('dish_recipe.recipe.attachment')
        RecipeCostPrice = pool.get('dish_recipe.recipe.cost_price')

        company = create_company()
        with set_company(company):
            service = self._create_product('service', 'Unit', service=True)
            recipe = Recipe(
                product=service,
            )
            recipe.save()
            self._check_nums(
                recipe, Decimal('0.0'), Decimal('0.0'), Decimal('0.0'))

            product_1 = self._create_product('product_1', 'Kilogram')
            product_2 = self._create_product('product_1', 'Pound')

            self._add_component(recipe, product_1, 250)
            self._add_component(recipe, product_2, 600)

            # Change cost (probably with a purchase)
            product_1.cost_price = Decimal('1000.0')
            product_1.save()
            # still cost=0.0, need a cost/price process
            self._check_nums(
                recipe, Decimal('0.0'), Decimal('0.0'), Decimal('0.0'))

            cost_price = RecipeCostPrice(
                recipe=recipe,
            )
            cost_price.update_cost_price()
            recipe.cost_price = (cost_price,)
            recipe.save()
            self._check_nums(
                recipe, Decimal('1000.0'), Decimal('0.0'), Decimal('0.0'))

    def _check_nums(self, recipe, cost, price, percentage):
        self.assertEqual(cost, recipe.cost)
        self.assertEqual(price, recipe.price)
        self.assertEqual(percentage, recipe.percentage)

    def _add_component(self, recipe, product, qty):
        RecipeComponent = Pool().get('dish_recipe.recipe.component')
        uom = self._get_uom('Gram')

        component = RecipeComponent(
            recipe=recipe,
            product=product,
            quantity=qty,
            unit=uom,
        )
        component.save()

        return component

    @classmethod
    def _create_product(cls, name, uom_name, service=False):
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        uom = cls._get_uom(uom_name)

        type_ = 'goods'
        if service:
            type_ = 'service'

        template=Template(
            name=name,
            default_uom=uom,
            type=type_,)
        template.save()

        product = Product(
            template=template
        )
        product.save()
        return product

    @classmethod
    def _get_uom(cls, name):
        Uom = Pool().get('product.uom')
        # Kilogram, Gram, Unit
        uom = Uom.search([('name', '=', name)])[0]
        return uom


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        DishRecipeTestCase))
    return suite
