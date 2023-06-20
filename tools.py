#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool


def tool_get_html_field_text(model, field, id_res, text, lang):
    pool = Pool()
    Trans = pool.get('ir.translation')

    if lang in (None, ''):
        res = text.replace('\n', '<br/>')
        return res

    vals = Trans.search([
        ('type', '=', 'model'),
        ('name', '=', model + ',' + field),
        ('res_id', '=', id_res),
        ('lang', '=', lang)
        ])
    if vals:
        res = vals[0].value
    else:
        res = text
    res = res.replace('\n', '<br/>')
    return res
