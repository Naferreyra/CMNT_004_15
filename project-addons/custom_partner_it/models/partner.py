##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@pcomunitea.com>$
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

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    codice_destinatario = fields.Char(required=True)

    electronic_invoice_subjected = fields.Boolean(default=False)

    @api.onchange('prospective', 'country_id')
    def onchange_prospective(self):
        self.electronic_invoice_subjected = False
        self.codice_destinatario = 'XXXXXXX'
        if not self.prospective and self.country_id.code == 'IT':
            self.electronic_invoice_subjected = True
            self.codice_destinatario = '0000000'

