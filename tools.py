#This file is part of tryton-dish_recipe project. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
import base64


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


def tool_get_html_base64_image(recipe, image_name, code='image/jpeg'):
    att_res = None
    binary_data = None
    res = None
    for att in recipe.attachments:
        if att.name == image_name:
            binary_data = att.data
            break
    if binary_data is not None:
        base64_encoded_data = base64.b64encode(binary_data)
        res = code + ';base64, ' + base64_encoded_data.decode('utf-8')
    return res
