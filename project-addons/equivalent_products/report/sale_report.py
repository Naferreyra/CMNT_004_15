# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    tag_id = fields.Many2one('product.tag', 'Tag')

    def _select(self):
        select_str = """, ptr.tag_id as tag_id"""
        return super(SaleReport, self)._select() + select_str

    def _from(self):
        from_str = """ left join product_tag_rel ptr on (ptr.product_id=l.product_id) """
        return super(SaleReport, self)._from() + from_str

    def _group_by(self):
        group_by_str = """, ptr.tag_id"""
        return super(SaleReport, self)._group_by() + group_by_str
