# See LICENSE file for full copyright and licensing details.

import time
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BaseSynchroServer(models.Model):
    """Class to store the information regarding server."""
    _name = "base.synchro.server"
    _description = "Synchronized server"

    name = fields.Char('Server name', required=True)
    server_url = fields.Char('Server URL', required=True)
    server_port = fields.Integer('Server Port', required=True, default=8069)
    server_db = fields.Char('Server Database', required=True)
    login = fields.Char('User Name', required=True)
    password = fields.Char('Password', required=True)
    obj_ids = fields.One2many('base.synchro.obj', 'server_id', 'Models',
                              ondelete='cascade')

    @api.model
    def sync_databases(self):
        for server in self.search([]):
            wzd = self.env['base.synchro'].\
                create({'server_url': server.id})
            wzd.upload_download()


class BaseSynchroObj(models.Model):
    """Class to store the operations done by wizard."""
    _name = "base.synchro.obj"
    _description = "Register Class"
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    domain = fields.Char('Domain', required=True, default='[]')
    server_id = fields.Many2one('base.synchro.server', 'Server',
                                ondelete='cascade', required=True)
    model_id = fields.Many2one('ir.model', string='Object to synchronize',
                               required=True)
    action = fields.Selection([('d', 'Download'), ('u', 'Upload'),
                               ('b', 'Both')], 'Synchronization direction',
                              required=True,
                              default='d')
    only_create_date = fields.Boolean("Only create date")
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', default=True)
    synchronize_date = fields.Datetime('Latest Synchronization', readonly=True)
    line_id = fields.One2many('base.synchro.obj.line', 'obj_id',
                              'IDs Affected', ondelete='cascade')
    avoid_ids = fields.One2many('base.synchro.obj.avoid', 'obj_id',
                                'Fields Not Sync.')
    context = fields.Text('Context',
                          help="Dictionary format. Used on create/write")

    force_ids = fields.One2many('base.synchro.obj.force', 'obj_id',
                                'Fields Force Sync.')

    @api.model
    def get_ids(self, model, dt, domain=None, action=None,
                only_create_date=False, flds=[], records_limit=1000, force_update=False):
        if action is None:
            action = {}
        action = action.get('action', 'd')
        pool = self.env[model]
        result = []
        data = []
        if not force_update:
            if dt and only_create_date:
                domain += [('create_date', '>=', dt)]
            elif dt:
                domain += ['|', ('create_date', '>=', dt),
                           ('write_date', '>=', dt)]
        offset = 0
        limit = 100
        obj_rec = pool.search(domain, limit=limit, offset=offset)
        while obj_rec and offset < records_limit:
            res = obj_rec.read(flds)
            data.extend(res)
            _logger.debug("RES: {}".format(res))
            offset += 100
            obj_rec = pool.search(domain, limit=limit, offset=offset)

        for r in data:
            result.append((r['create_date'], r['id'],
                           action, r))
        return result


class BaseSynchroObjAvoid(models.Model):
    """Class to avoid the base synchro object."""
    _name = "base.synchro.obj.avoid"
    _description = "Fields to not synchronize"

    name = fields.Char('Field Name', required=True)
    obj_id = fields.Many2one('base.synchro.obj', 'Object', required=True,
                             ondelete='cascade')

class BaseSynchroObjForce(models.Model):
    """Class to force the base synchro object."""
    _name = "base.synchro.obj.force"
    _description = "Fields to force synchronize"

    name = fields.Char('Field Name', required=True)
    obj_id = fields.Many2one('base.synchro.obj', 'Object', required=True,
                             ondelete='cascade')
    type = fields.Char('Field Type', required=True)


class BaseSynchroObjLine(models.Model):
    """Class to store object line in base synchro."""
    _name = "base.synchro.obj.line"
    _description = "Synchronized instances"

    name = fields.Datetime('Date', required=True,
                           default=lambda *args:
                           time.strftime('%Y-%m-%d %H:%M:%S'))
    obj_id = fields.Many2one('base.synchro.obj', 'Object', ondelete='cascade')
    local_id = fields.Integer('Local ID', readonly=True)
    remote_id = fields.Integer('Remote ID', readonly=True)
