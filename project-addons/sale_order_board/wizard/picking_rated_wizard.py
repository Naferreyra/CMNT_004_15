##############################################################################
#
#    Author: Jesus Garcia Manzanas
#    Copyright 2018 Visiotech
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from odoo import models, fields
from odoo.addons import decimal_precision as dp


class PickingRatedWizard(models.TransientModel):
    _name = 'picking.rated.wizard'

    total_weight = fields.Char('Total Weight (Kgs)', readonly=True, digits=dp.get_precision('Stock Weight'))
    products_wo_weight = fields.Char('', readonly=True)
    data = fields.One2many('picking.rated.wizard.tree', 'wizard_id', string='Shipping Data', readonly=True)
    products_without_weight = fields.Char('', readonly=True)
    message_error = fields.Text('', readonly=True)


class PickingRatedWizardTree(models.TransientModel):
    _name = 'picking.rated.wizard.tree'
    _order = 'amount asc'

    wizard_id = fields.Many2one('picking.rated.wizard')
    order_id = fields.Many2one('sale.order', 'Order')
    currency = fields.Char('Currency')
    amount = fields.Float('Amount')
    service = fields.Char('Service')
    transit_time = fields.Char('Arrival')
