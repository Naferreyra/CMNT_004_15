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
import logging

_logger = logging.getLogger(__name__)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        _logger.info("STARTING CALL SUPER SCHEDULER")
        super()._run_scheduler_tasks(use_new_cursor=use_new_cursor,
                                     company_id=company_id)
        _logger.info("SEARCHING FOR INTERNAL PICKINGS")
        operation_internal = self.env.ref('stock.picking_type_internal').id
        pick_ids_assign = self.env["stock.picking"]. \
            search([("picking_type_id", "=",
                     operation_internal),
                    ("state", "=", "assigned")])

        pick_ids_confirmed = self.env["stock.picking"]. \
            search([("picking_type_id", "=",
                     operation_internal),
                    ("state", "=", "confirmed"), ('move_type', '!=', 'direct')])
        max_commit_len = int(self.env['ir.config_parameter'].sudo().get_param('max_commit_len'))
        len_pick_assign = len(pick_ids_assign)

        _logger.info("TRANSFERRING READY INTERNAL PICKINGS")
        for count, pick_assign in enumerate(pick_ids_assign):
            pick_assign.action_done()
            if ((count + 1 >= max_commit_len and count + 1 % max_commit_len == 0) or count == len_pick_assign - 1) \
                    and use_new_cursor:
                self.env.cr.commit()

        _logger.info("PROCESSING CONFIRMED AND PARTIALLY AVAILABLE PICKINGS")
        if pick_ids_confirmed:
            pick_ids_confirmed.write({'move_type': 'direct'})
        pick_ids_par = self.env["stock.picking"]. \
            search([("picking_type_id", "=",
                     operation_internal),
                    ("state", "=", "partially_available")])

        pick_ids_par.write({'move_type': 'direct'})
        for count, pick_partially in enumerate(pick_ids_par):
            pick_partially.action_copy_reserv_qty()
            pick_partially.action_accept_confirmed_qty()
            if count + 1 >= max_commit_len and count + 1 % max_commit_len == 0 and use_new_cursor:
                self.env.cr.commit()

        if use_new_cursor:
            self.env.cr.commit()
        _logger.info("DONE")

