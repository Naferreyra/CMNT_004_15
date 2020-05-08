from odoo import models, fields, _, exceptions, api


class KitchenCustomization(models.Model):
    _name = 'kitchen.customization'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('commercial_id')
    def _compute_is_manager(self):
        self.is_manager = self.env.user.has_group('kitchen.group_kitchen')

    is_manager = fields.Boolean(compute='_compute_is_manager',default=True)
    name = fields.Char(default='New', readonly=True, string="Name")
    order_id = fields.Many2one('sale.order', string="Order")
    type_ids = fields.Many2many('customization.type', required=1, string="Type")
    commercial_id = fields.Many2one('res.users', required=1, string="Commercial")
    partner_id = fields.Many2one('res.partner', string="Partner")
    user = fields.Char(readonly=True, string="User")
    date_customization = fields.Datetime('Order Date', required=True, index=True, copy=False,
                                         default=fields.Datetime.now)
    customization_line = fields.One2many('kitchen.customization.line', 'customization_id')

    notify_users = fields.Many2many('res.users')

    state = fields.Selection([
        ('draft', 'New'),
        ('sent', 'Sent'),
        ('in_progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Customization Status', readonly=True, copy=False, index=True, track_visibility='onchange',
        default='draft')

    erase_logo = fields.Boolean()
    date_planned = fields.Datetime()
    comments = fields.Text(string='Comments')

    def _compute_products_format(self):
        for customization in self:
            customization.products_qty_format = ""
            for line in customization.customization_line:
                only_logo = _("(ONLY LOGO)") if line.only_erase_logo else ""
                customization.products_qty_format += ' %i * %s%s;' % (line.product_qty, line.product_id.default_code,only_logo)

    products_qty_format = fields.Char(compute="_compute_products_format")

    def action_done(self):
        self.state = 'done'
        template = self.env.ref('kitchen.send_mail_to_commercials_customization_done')
        ctx = dict()
        ctx.update({
            'email_to': self.commercial_id.login,
            'email_cc': ','.join(self.notify_users.mapped('email')),
            'lang': self.commercial_id.lang
        })
        template.with_context(ctx).send_mail(self.id)

    def action_confirm(self):
        if not self.customization_line:
            raise exceptions.UserError(_('Please add some products before confirming the customization request'))
        if any(self.customization_line.mapped('product_qty')<=0):
            raise exceptions.UserError(_("You can't create a customization with a quantity of less than one of a product"))
        self.state = 'sent'
        template = self.env.ref('kitchen.send_mail_to_kitchen_customization_sent')
        ctx = dict()
        ctx.update({
            'lang': 'es_ES'
        })
        template.with_context(ctx).send_mail(self.id)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('customization.name') or '/'
        if vals.get('order_id', False):
            self.env['sale.order'].browse(vals.get('order_id')).message_post(
                body=_("The order contains customized products"))
        return super(KitchenCustomization, self).create(vals)

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'



class KitchenCustomizationLine(models.Model):
    _name = 'kitchen.customization.line'

    product_id = fields.Many2one('product.product', required=1)
    product_qty = fields.Float(required=1)
    customization_id = fields.Many2one('kitchen.customization', ondelete='cascade', required=True, index=True,
                                       copy=False)
    sale_line_id = fields.Many2one('sale.order.line')
    state = fields.Selection([
        ('draft', 'New'),
        ('sent', 'Sent'),
        ('in_progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], related='customization_id.state', string='status', readonly=True, copy=False, store=True,
        default='draft')
    only_erase_logo = fields.Boolean()
