#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields,  sequence_ordered
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, If
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.modules.product import price_digits
from trytond.modules.account.tax import _TaxKey
from decimal import Decimal
import base64
from . tools import tool_get_html_field_text, tool_get_html_base64_image


class Recipe(ModelSQL, ModelView, sequence_ordered(), CompanyMultiValueMixin):
    'Dish Recipe'
    __name__ = 'dish_recipe.recipe'
    name = fields.Char('Name', required=True, translate=True)
    description = fields.Text('Description', translate=True, size=None)
    preparation = fields.Text('Preparation')
    category = fields.Many2One('dish_recipe.category',
        'Category', required=True)
    components = fields.One2Many('dish_recipe.recipe.component',
        'recipe', 'Component')
    subrecipes = fields.One2Many('dish_recipe.recipe.subrecipe',
        'recipe', 'Sub Recipe',
        domain=[
            ('id', '!=', Eval('id')),
        ], depends=['id'])
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    cost_components = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost_components')
    cost_last_components = fields.Function(fields.Numeric('Last Cost',
            digits=price_digits),
        'get_cost_components')
    cost_subrecipes = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost_subrecipes')
    cost_last_subrecipes = fields.Function(fields.Numeric('Last Cost',
            digits=price_digits),
        'get_cost_subrecipes')
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'get_cost')
    cost_last = fields.Function(fields.Numeric('Last Cost',
            digits=price_digits),
        'get_cost')
    price = fields.MultiValue(fields.Numeric('Price',
            digits=price_digits))
    prices = fields.One2Many(
        'dish_recipe.price', 'recipe', 'Prices')
    percentage = fields.Function(fields.Numeric('Percentage',
            digits=price_digits),
        'get_percentage')
    percentage_last = fields.Function(fields.Numeric('Percentage',
            digits=price_digits),
        'get_percentage')
    product = fields.Many2One('product.product', 'Product associated',
        help='Product associated with this recipe.')
    info_1 = fields.Char('Info 1')
    info_2 = fields.Char('Info 2')
    info_3 = fields.Char('Info 3')
    publish = fields.MultiValue(fields.Boolean('Publish'))
    publishes = fields.One2Many(
        'dish_recipe.publish', 'recipe', 'Puplishes')
    active = fields.Boolean('Active')

    @classmethod
    def __register__(cls, module_name):
        super(Recipe, cls).__register__(module_name)
        table = cls.__table_handler__(module_name)
        # Migration from 5.8.0:
        if table.column_exist('quantity'):
            table.drop_column('quantity')
            table.drop_column('unit')

    @classmethod
    def __setup__(cls):
        super(Recipe, cls).__setup__()
        cls._order = [
            ('sequence', 'ASC'),
            ('name', 'DESC'),
            ('id', 'DESC'),
            ]

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'price':
            return pool.get('dish_recipe.price')
        elif field == 'publish':
            return pool.get('dish_recipe.publish')
        return super(Recipe, cls).multivalue_model(field)

    @staticmethod
    def default_active():
        return True

    def get_html_field_text(self, field, lang):
        text = getattr(self, field)
        res = tool_get_html_field_text(
                'dish_recipe.recipe', field, self.id, text, lang)        
        return res

    def get_html_price(self, field, lang='en', company=1):
        pool = Pool()
        Lang = pool.get('ir.lang')
        Price = pool.get('dish_recipe.price')

        prices = Price.search([
            ('company', '=', company),
            ('recipe', '=', self.id),
            ])
        res = None
        if prices:
            res = prices[0].price
        if not res:
            res = Decimal('0.0')

        lang, = Lang.search([
                ('code', '=', lang),
                ])
        res = Lang.format(lang,
            '%.2f',
            res, True)
        return res

    def get_html_base64_image(self, image_name, code='image/jpeg',
            default_image=None):
        pool = Pool()
        res = None
        if image_name:
            if image_name.startswith("[["):
                Recipe = pool.get('dish_recipe.recipe')
                end = image_name.find(']].')
                if end > -1:
                    recipe_id = int(image_name[2:end])
                    image_name = image_name[end+3:]
                    res = tool_get_html_base64_image(Recipe(recipe_id),
                            image_name, code)
            else:
                res = tool_get_html_base64_image(self,
                        image_name, code)
        if res is None and default_image is not None:
            res = self.get_html_base64_image(default_image, code=code)
        if res is None:
            res = ''
        return res

    def can_publish(self, company=1):
        if not self.active:
            return
        pool = Pool()
        Publish = pool.get('dish_recipe.publish')
        publishes = Publish.search([
            ('company', '=', company),
            ('recipe', '=', self.id),
            ])
        res = None
        if publishes:
            res = publishes[0].publish
        return res

    def get_cost_components(self, name=None):
        if name == 'cost_components':
            field = 'total_cost'
        elif name == 'cost_last_components':
            field = 'total_cost_last'
        return self.get_total_sub_cost('components', field)

    def get_cost_subrecipes(self, name=None):
        if name == 'cost_subrecipes':
            field = 'total_cost'
        elif name == 'cost_last_subrecipes':
            field = 'total_cost_last'
        return self.get_total_sub_cost('subrecipes', field)

    def get_total_sub_cost(self, main, field):
        result = Decimal('0.0')
        for el in getattr(self, main):
            if getattr(el, field):
                result += getattr(el, field)
        exp = Decimal(str(10.0 ** -price_digits[1]))
        return result.quantize(exp)

    def get_cost(self, name=None):
        if name == 'cost':
            return self.cost_components + self.cost_subrecipes
        elif name == 'cost_last':
            return self.cost_last_components + self.cost_last_subrecipes

    def get_percentage(self, name=None):
        if name == 'percentage':
            field = 'cost'
        elif name == 'percentage_last':
            field = 'cost_last'
        if self.price is None or getattr(self, field) is None:
            return
        result = getattr(self, field) / self.price * Decimal('100.0')
        exp = Decimal(str(10.0 ** -price_digits[1]))
        return result.quantize(exp)

    @fields.depends('cost', 'cost_last', 'percentage',
            'percentage_last', 'components', 'subrecipes',
            'price')
    def on_change_price(self):
        self.cost_components = self.get_cost_components(
                name='cost_components')
        self.cost_last_components = self.get_cost_components(
                name='cost_last_components')
        self.cost_subrecipes = self.get_cost_subrecipes(
                name='cost_subrecipes')
        self.cost_last_subrecipes = self.get_cost_subrecipes(
                name='cost_last_subrecipes')
        self.cost = self.get_cost(name='cost')
        self.cost_last = self.get_cost(name='cost_last')
        self.percentage = self.get_percentage(name='percentage')
        self.percentage_last = self.get_percentage(name='percentage_last')

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
                        gettext('dish_recipe_product.msg_product_selected',
                            product=product.rec_name,
                            recipe=recipe.rec_name,
                            rcp=rcp.rec_name))
        super(Recipe, cls).validate(recipes)


class RecipePrice(ModelSQL, CompanyValueMixin):
    "Recipe Price"
    __name__ = 'dish_recipe.price'
    recipe = fields.Many2One(
        'dish_recipe.recipe', 'Recipe', ondelete='CASCADE')
    price = fields.Numeric("Price", digits=price_digits)


class RecipePublish(ModelSQL, CompanyValueMixin):
    "Recipe Publish"
    __name__ = 'dish_recipe.publish'
    recipe = fields.Many2One(
        'dish_recipe.recipe', 'Recipe', ondelete='CASCADE')
    publish = fields.Boolean("Publish")


class SubRecipe(ModelSQL, ModelView):
    'Sub Recipe'
    __name__ = 'dish_recipe.recipe.subrecipe'

    recipe = fields.Many2One('dish_recipe.recipe', 'Recipe',
        ondelete='CASCADE', required=True)
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
    cost_last = fields.Function(fields.Numeric('Last Cost',
            digits=price_digits),
        'get_cost')
    total_cost = fields.Function(fields.Numeric('Total Cost',
            digits=price_digits),
        'get_total_cost')
    total_cost_last = fields.Function(fields.Numeric('Total Last Cost',
            digits=price_digits),
        'get_total_cost')

    def get_unit_digits(self, name=None):
        return price_digits[1]

    def get_cost(self, name=None):
        if not self.subrecipe:
            return Decimal('0.0')
        return getattr(self, name)

    def get_total_cost(self, name=None):
        if not self.quantity:
            return Decimal('0.0')
        if name == 'total_cost':
            field = 'cost'
        else:
            field = 'cost_last'
        return getattr(self, field) * Decimal(self.quantity)

    @fields.depends('quantity', 'subrecipe')
    def on_change_subrecipe(self):
        self.cost = self.get_cost(name='cost')
        self.cost_last = self.get_cost(name='cost_last')
        self.total_cost = self.get_total_cost(name='total_cost')
        self.total_cost_last = self.get_total_cost(name='total_cost_last')

    @fields.depends(methods=['on_change_subrecipe'])
    def on_change_quantity(self):
        self.on_change_subrecipe()


class RecipeComponent(ModelSQL, ModelView):
    'Recipe Component'
    __name__ = 'dish_recipe.recipe.component'

    recipe = fields.Many2One('dish_recipe.recipe', 'Recipe',
        ondelete='CASCADE', required=True)
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    product = fields.Many2One('product.product', 'Product', required=True,
        domain=[('id', '!=', -1)])
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
    waste = fields.Float('Waste Percentage', digits=price_digits)
    taxes = fields.Boolean('Include taxes')
    cost = fields.Function(fields.Numeric('Cost',
            digits=price_digits),
        'on_change_with_cost')
    cost_last = fields.Function(fields.Numeric('Last Cost',
            digits=price_digits),
        'on_change_with_cost_last')
    total_cost = fields.Function(fields.Numeric('Total Cost',
            digits=price_digits),
        'on_change_with_total_cost')
    total_cost_last = fields.Function(fields.Numeric('Total Last Cost',
            digits=price_digits),
        'on_change_with_total_cost_last')

    @fields.depends('unit')
    def on_change_with_unit_digits(self, name=None):
        if self.unit:
            return self.unit.digits
        return 2

    @fields.depends('product')
    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id

    @fields.depends('product', 'unit', 'taxes')
    def on_change_with_cost(self, name=None):
        return self._calculate_cost(
                name, self.product, self.unit, self.taxes)

    @fields.depends('product', 'unit', 'taxes')
    def on_change_with_cost_last(self, name=None):
        return self._calculate_cost(
                name, self.product, self.unit, self.taxes)

    @fields.depends('quantity', 'cost', 'waste',
            'taxes', 'unit')
    def on_change_with_total_cost(self, name=None):
        return self._get_total_cost(
                'cost', self.quantity, self.waste)

    @fields.depends('quantity', 'cost_last', 'waste',
            'taxes', 'unit')
    def on_change_with_total_cost_last(self, name=None):
        return self._get_total_cost(
                'cost_last', self.quantity, self.waste)

    def _get_total_cost(self, name, quantity, waste):
        if not quantity:
            return Decimal('0.0')
        total = getattr(self, name) * Decimal(quantity)
        if self.waste and (waste > 0 and waste < 100):
            waste_t = total * Decimal((waste / 100))
            total += waste_t
        return total

    def _calculate_cost(self, name, product, unit, include_tax):
        if not product or not unit:
            return Decimal('0.0')
        Uom = Pool().get('product.uom')
        cost = None
        if name == 'cost':
            cost = Uom.compute_price(
                product.default_uom,
                product.cost_price,
                unit)
        elif name == 'cost_last':
            l_cost, l_unit = self._get_last_cost(product)
            if l_unit is not None:
                cost = Uom.compute_price(
                    l_unit,
                    l_cost,
                    unit)

        if cost is None:
            return Decimal('0.0')
        res = cost
        if include_tax:
            tax_amount = self._compute_taxes(product, cost)
            res = cost + tax_amount
        return res

    def _get_last_cost(self, product,
            date=None, company=None):
        if not product:
            return Decimal('0.0')
        pool = Pool()
        Line = pool.get('account.invoice.line')

        if company is None:
            company = Transaction().context.get('company')
        domain = [
                ('invoice.company', '=', company),
                ('invoice.state', 'in', ['posted', 'paid']),
                ('type', '=', 'line'),
                ('product', '=', product.id),
                ('unit_price', '>', 0),
            ]
        if date:
            domain.append(('invoice.invoice_date', '<=', date))

        lines = Line.search(domain,
            order=[('invoice.invoice_date', 'DESC'), ('id', 'DESC')],
            limit=1)
        if lines:
            return lines[0].unit_price, lines[0].unit
        return None, None

    def _compute_taxes(self, product, cost):
        pool = Pool()
        Tax = pool.get('account.tax')
        Company = pool.get('company.company')

        tax_ids = []
        taxes = {}
        currency = None

        company_id = Transaction().context.get('company', None)
        if company_id is not None:
            currency = Company(company_id).currency

        print(product.name)

        for tax in product.supplier_taxes_used:
            tax_ids.append(tax.id)

        l_taxes = Tax.compute(Tax.browse(tax_ids), cost, 1, None)
        #print(l_taxes)

        for tax in l_taxes:
            taxline = self._compute_tax_line(**tax)
            # Base must always be rounded per line as there will be one
            # tax line per taxable_lines
            if currency is not None:
                taxline['base'] = currency.round(taxline['base'])
            if taxline not in taxes:
                taxes[taxline] = taxline
            else:
                taxes[taxline]['base'] += taxline['base']
                taxes[taxline]['amount'] += taxline['amount']

        self._round_taxes(taxes, currency)
        res = Decimal('0.0')
        for tx in taxes.items():
            res = tx[0]['amount']
        return res

    @staticmethod
    def _compute_tax_line(amount, base, tax):
        if base >= 0:
            type_ = 'invoice'
        else:
            type_ = 'credit_note'

        line = {}
        line['manual'] = False
        line['description'] = tax.description
        line['legal_notice'] = tax.legal_notice
        line['base'] = base
        line['amount'] = amount
        line['tax'] = tax.id
        line['account'] = getattr(tax, '%s_account' % type_).id

        return _TaxKey(**line)

    @staticmethod
    def _round_taxes(taxes, currency):
        if not currency:
            return
        for taxline in taxes.values():
            taxline['amount'] = currency.round(taxline['amount'])
