from odoo import models, fields


class Picking(models.Model):
    _inherit = "stock.picking"

    name = fields.Char(index=False)
    origin = fields.Char(index=False)
    date = fields.Datetime(index=False)
    priority = fields.Selection(index=False)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    name = fields.Char(index=False)


class StockMove(models.Model):
    _inherit = "stock.move"

    name = fields.Char(index=False)
    create_date = fields.Datetime(index=False)
    date_expected = fields.Datetime(index=False)


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    company_id = fields.Many2one(index=False)
    location_id = fields.Many2one(index=False)
    package_id = fields.Many2one(index=False)


class Inventory(models.Model):
    _inherit = "stock.inventory"

    company_id = fields.Many2one(index=False)
