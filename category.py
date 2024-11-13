# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields, tree, sequence_ordered
from trytond.pyson import Eval
from . tools import tool_get_html_field_text


class Category(tree(separator=' / '), sequence_ordered(), ModelSQL, ModelView):
    "Recipe Category"
    __name__ = "dish_recipe.category"
    name = fields.Char('Name', required=True, translate=True)
    parent = fields.Many2One('dish_recipe.category', 'Parent',
        domain=[
            ('id', '!=', Eval('id', None)),
        ], depends=['id'])
    childs = fields.One2Many('dish_recipe.category', 'parent',
            string='Children')
    recipes = fields.One2Many('dish_recipe.recipe',
            'category', 'Recipes')
    info_1 = fields.Char('Info 1')
    info_2 = fields.Char('Info 2')
    info_3 = fields.Char('Info 3')

    @classmethod
    def __setup__(cls):
        super(Category, cls).__setup__()
        cls._order = [
            ('sequence', 'ASC'),
            ('name', 'DESC'),
            ('id', 'DESC'),
            ]

    def get_html_field_text(self, field, lang):
        text = getattr(self, field)
        res = tool_get_html_field_text(
                'dish_recipe.category', field, self.id, text, lang)

        #pool = Pool()
        #Trans = pool.get('ir.translation')

        #if lang in (None, ''):
        #    res = getattr(self, field)
        #    res = res.replace('\n', '<br/>')
        #    return res

        #vals = Trans.search([
        #    ('type', '=', 'model'),
        #    ('name', '=', 'dish_recipe.recipe,' + field),
        #    ('res_id', '=', self.id),
        #    ('lang', '=', lang)
        #    ])
        #if vals:
        #    res = vals[0].value
        #else:
        #    res = getattr(self, field)
        #res = res.replace('\n', '<br/>')
        
        return res
