##############################################################################
#
#    Copyright (C) 2016 Comunitea Servicios Tecnológicos S.L.
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
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

from odoo import models, api


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super()._run_scheduler_tasks(use_new_cursor=use_new_cursor,
                                     company_id=company_id)
        location_it = self.env['stock.location'].search([('name', '=', 'Depósito Visiotech Italia')])
        operation_it = self.env['stock.picking.type'].search([('name', '=', 'Albarán de salida desde depósito IT')])
        pick_ids = self.env["stock.picking"].\
            search([("picking_type_id", "=",
                     self.env.ref('stock.picking_type_internal').id),
                    ("state", "in", ("assigned", "confirmed", "partially_available"))])
        # Italy pickings
        pick_ids += self.env["stock.picking"].\
            search([("location_id", "=", location_it.id),
                    ("picking_type_id", "=", operation_it.id),
                    ("state", "in", ("assigned", "confirmed", "partially_available"))])

        for pick_assign in pick_ids.filtered(
                lambda l: l.state == "assigned"):
            pick_assign.action_done()
        for pick_partially in pick_ids.filtered(
                lambda l: l.state in ("confirmed", "partially_available")):
            pick_partially.move_type = 'direct'
            if pick_partially.state == "partially_available":
                pick_partially.action_copy_reserv_qty()
                pick_partially.action_accept_confirmed_qty()

        if use_new_cursor:
            self.env.cr.commit()
