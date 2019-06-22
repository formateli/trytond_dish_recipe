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
        Product = pool.get('product.product')

        recipe_id = None
        product_1_id = None
        product_2_id = None

        company_a = create_company(name='Company A')
        company_b = create_company(name='Company B')

        service = self._create_product('service', 'Unit', service=True)
        recipe = Recipe(
            product=service,
        )
        recipe.save()
        recipe_id = recipe.id
        self._check_nums(recipe, None, None, None)

        product_1 = self._create_product('product_1', 'Kilogram')
        product_1_id = product_1.id
        product_2 = self._create_product('product_1', 'Pound')
        product_2_id = product_2.id

        self._add_component(recipe, product_1, 250)
        self._add_component(recipe, product_2, 600)

        self._check_nums(recipe, Decimal('0.0'), None, None)

        with set_company(company_a):
            # Change cost (probably with a purchase)
            self._update_product_cost(product_1_id, Decimal('1000.0'))

        with set_company(company_b):
            # Change cost (probably with a purchase)
            self._update_product_cost(product_1_id, Decimal('2000.0'))

        with set_company(company_a):
            recipe = Recipe(recipe_id)
            self._check_nums(recipe, Decimal('250.0'), None, None)
            recipe.price = Decimal('500.0')
            recipe.save()

        with set_company(company_b):
            recipe = Recipe(recipe_id)
            self._check_nums(recipe, Decimal('500.0'), None, None)
            recipe.price = Decimal('800.0')
            recipe.save()

        with set_company(company_a):
            recipe = Recipe(recipe_id)
            self._check_nums(recipe,
                Decimal('250.0'), Decimal('500.0'), Decimal('50.0'))

        with set_company(company_b):
            recipe = Recipe(recipe_id)
            self._check_nums(recipe,
                Decimal('500.0'), Decimal('800.0'), Decimal('62.5'))

    def _check_nums(self, recipe, cost, price, percentage):
        self.assertEqual(cost, recipe.cost)
        self.assertEqual(price, recipe.price)
        self.assertEqual(percentage, recipe.percentage)

    def _update_product_cost(self, product_id, cost):
        Product = Pool().get('product.product')
        product = Product(product_id)
        product.cost_price = cost
        product.save()
        return product

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
