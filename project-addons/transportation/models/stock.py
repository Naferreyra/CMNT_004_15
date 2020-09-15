##############################################################################
#
#    Author: Omar Castiñeira Saavedra
#    Copyright 2015 Comunitea Servicios Tecnológicos S.L.
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

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
import requests
import json


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.multi
    @api.depends('move_lines.state', 'move_lines.picking_id',
                 'move_lines.product_id', 'move_lines.product_uom_qty',
                 'move_lines.product_uom')
    def cal_weight(self):
        for picking in self:
            total_weight = total_weight_net = 0.00
            for move in picking.move_lines:
                if move.state != 'cancel':
                    total_weight += move.weight
                    total_weight_net += move.weight_net
            if picking.weight_st:
                total_weight = picking.weight_st
            if picking.weight_net_st:
                total_weight_net = picking.weight_net_st
            picking.weight = total_weight
            picking.weight_net = total_weight_net

    @api.model
    def _get_default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm')
        return self.env['product.uom'].search([('category_id', '=',
                                                uom_categ_id.id),
                                               ('factor', '=', 1)])[0]

    @api.multi
    def button_check_tracking(self):
        # TODO: Revisar este botón al tener datos de tracking
        carrier_ref = self.carrier_tracking_ref
        carrier = self.carrier_name
        status_list = self.env['picking.tracking.status.list']
        url = self.env['ir.config_parameter'].sudo().get_param('url.visiotech.web.tracking')
        password = self.env['ir.config_parameter'].sudo().get_param('url.visiotech.web.tracking.pass')
        language = self.env.user.lang or u'es_ES'
        if 'Correos' in carrier:
            carrier_ref = carrier_ref[-13:]
        elif 'UPS' in carrier:
            carrier_ref = carrier_ref[:35]

        data = {'request_API': {
                    "numRef": carrier_ref,
                    "transportista": carrier,
                    "password": password,
                    "language": language
        }}

        response = requests.session().post(url, data=json.dumps(data))
        if response.status_code != 200:
            raise Exception(response.text)
        if 'error' in response.url:
            raise Exception("Could not find information on url '%s'" % response.url)
        info = json.loads(response.text)

        # Update picking field "number of packages"
        if info['Num_bags']:
            self.number_of_packages = info['Num_bags']

        view_id = self.env['picking.tracking.status']
        ctx = {'information': info}
        new = view_id.with_context(ctx).create({})
        # Update wizard field "num packages"
        new.write({'num_packages': info['Num_bags']})
        status_list.search([('picking_id', '=', self.id)]).unlink()

        if info["Bags"]:
            for package in info["Bags"]:
                info_package = info["Bags"][package]
                data_status = {
                    'wizard_id': new.id,
                    'picking_id': self.id,
                    'packages_reference': info_package["Tracking"][0] + ' (x' + str(info_package["Num_bags"]) + ')',
                    'status': package.upper()
                }
                new.write({'status_list': [(0, 0, data_status)]})
                last_status = True
                for status in info_package["Activity"]:
                    city_country = status["City"]
                    if status["Country"]:
                        city_country += ' (' + status["Country"] + ')'

                    date_time = status["Date"] + ' ' + (status["Time"] if status["Time"] else "")

                    data_status = {
                        'wizard_id': new.id,
                        'picking_id': self.id,
                        'status': status["Status"],
                        'city': city_country,
                        'date': date_time,
                        'last_record': last_status
                    }
                    new.write({'status_list': [(0, 0, data_status)]})
                    last_status = False

        return {
            'name': 'Tracking status information',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'picking.tracking.status',
            'res_id': new.id,
            'src_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'id': 'action_picking_tracking_status',
        }

    @api.multi
    def write(self, vals):
        if 'weight' in vals:
            vals['weight_st'] = vals.get('weight')
        if 'weight_net' in vals:
            vals['weight_net_st'] = vals.get('weight_net')
        return super(StockPicking, self).write(vals)

    volume = fields.Float('Volume', copy=False)
    total_cbm = fields.Float('Total CBM')
    weight_st = fields.Float(digits=dp.get_precision('Stock Weight'))
    weight_net_st = fields.\
        Float(digits=dp.get_precision('Stock Weight'))
    weight = fields.Float('Weight', compute='cal_weight', readonly=False,
                          digits=dp.get_precision('Stock Weight'))
    weight_net = fields.Float('Net Weight', compute="cal_weight", readonly=False,
                              digits=dp.get_precision('Stock Weight'))
    carrier_tracking_ref = fields.Char('Carrier Tracking Ref', copy=False)
    number_of_packages = fields.Integer('Number of Packages', copy=False)
    weight_uom_id = fields.Many2one('product.uom', 'Unit of Measure',
                                    required=True, readonly="1",
                                    help="Unit of measurement for Weight",
                                    default=_get_default_uom)
    carrier_name = fields.Char("Carrier name")
    carrier_service = fields.Char("Carrier service")


class StockMove(models.Model):

    _inherit = 'stock.move'

    @api.multi
    @api.depends('product_id', 'product_uom_qty', 'product_uom', 'weight_st', 'weight_net_st')
    def _cal_move_weight(self):
        for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
            move.weight = (move.product_qty * move.product_id.weight)
            move.weight_net = (move.product_qty * move.product_id.weight_net)
            if move.weight_st:
                move.weight = move.weight_st
            if move.weight_net_st:
                move.weight_net = move.weight_net_st


    @api.model
    def _get_default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm')
        return self.env['product.uom'].search([('category_id', '=',
                                                uom_categ_id.id),
                                               ('factor', '=', 1)])[0]

    weight = fields.Float('Weight', compute='_cal_move_weight',
                          digits=dp.get_precision('Stock Weight'),
                          store=True, readonly=False)
    weight_net = fields.Float('Net weight', compute='_cal_move_weight',
                              digits=dp.get_precision('Stock Weight'),
                              store=True, readonly=False)
    weight_st = fields.Float(digits=dp.get_precision('Stock Weight'))
    weight_net_st = fields.\
        Float(digits=dp.get_precision('Stock Weight'))
    weight_uom_id = fields.Many2one('product.uom', 'Unit of Measure',
                                    required=True, readonly="1",
                                    help="Unit of Measure (Unit of Measure) "
                                         "is the unit of measurement for "
                                         "Weight", default=_get_default_uom)

    @api.multi
    def write(self, vals):
        if 'weight' in vals:
            vals['weight_st'] = vals.get('weight')
        if 'weight_net' in vals:
            vals['weight_net_st'] = vals.get('weight_net')
        return super(StockMove, self).write(vals)
