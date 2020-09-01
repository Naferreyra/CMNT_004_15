from odoo import models, fields, _, exceptions, api


class KitchenCustomization(models.Model):
    _name = 'kitchen.customization'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('commercial_id')
    def _compute_is_manager(self):
        self.is_manager = self.env.user.has_group('kitchen.group_kitchen')

    is_manager = fields.Boolean(compute='_compute_is_manager',default=True)
    name = fields.Char(default='New', readonly=True, string="Name")
    order_id = fields.Many2one('sale.order', string="Order",domain=[('state', '=', 'reserve')])
    commercial_id = fields.Many2one('res.users', required=1, string="Commercial")
    partner_id = fields.Many2one('res.partner', string="Partner")
    user = fields.Char(readonly=True, string="User")
    date_customization = fields.Datetime('Order Date', required=True, index=True, copy=False,
                                         default=fields.Datetime.now)
    customization_line = fields.One2many('kitchen.customization.line', 'customization_id')

    notify_users = fields.Many2many('res.users')

    state = fields.Selection([
        ('draft', 'New'),
        ('waiting','Waiting Availability'),
        ('sent', 'Sent'),
        ('in_progress', 'In Progress'),
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
        if any(self.customization_line.filtered(lambda l: l.product_qty <=0)):
            raise exceptions.UserError(_("You can't create a customization with a quantity of less than one of a product"))
        lines_without_type = self.customization_line.filtered(lambda l: not l.type_ids)
        if lines_without_type:
            raise exceptions.UserError(_(
                "You can't confirm a customization without a customization type: %s") % lines_without_type.mapped('product_id.default_code'))
        if self.order_id:
            customization_product_lines = set(self.customization_line.mapped('product_id.default_code'))
            order_product_lines = set(self.order_id.order_line.mapped('product_id.default_code'))
            if not customization_product_lines.issubset(order_product_lines):
                raise exceptions.UserError(_(
                    "You can't confirm a customization with products that not belong to the original order: %s") % str(customization_product_lines - order_product_lines))
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

    reservation_status = fields.Selection([
        ('waiting', 'Waiting Availability'),
        ('to customize', 'Fully Reserved')
    ], string='Reservation Status', compute='_compute_reservation_status', store=True, default='to customize')

    @api.depends('customization_line.reservation_status')
    def _compute_reservation_status(self):
        for customization in self:
            customization.reservation_status = "waiting"
            if customization.customization_line and all([x.reservation_status != "waiting" for x in customization.customization_line]):
                customization.action_confirm()
                customization.state = 'sent'
                customization.reservation_status = "to customize"

    @api.onchange('order_id')
    def onchange_order_id(self):
        if self.order_id:
            self.partner_id=self.order_id.partner_id
            self.commercial_id=self.order_id.user_id
            self.notify_users=[(6,0,[self.order_id.user_id.id])]
            self.customization_line=False
            for line in self.order_id.order_line.filtered(
                lambda l: not l.deposit and l.product_id.categ_id.with_context(
                    lang='es_ES').name != 'Portes' and l.price_unit >= 0):
                customization_qty = sum([x.get("product_qty",0) for x in self.env['kitchen.customization.line'].search_read([('sale_line_id','=',line.id),('state','!=','cancel')],['product_qty'])])
                if line.product_qty - customization_qty >0:
                    new_line = {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty - customization_qty,
                        'sale_line_id': line.id,
                        'customization_id': self.id
                    }
                    self.customization_line.new(new_line)

    def write(self, vals):
        res = super(KitchenCustomization, self).write(vals)
        if vals.get('date_planned', False):
            template = self.env.ref('kitchen.send_mail_to_commercials_date_planned_changed')
            ctx = dict()
            ctx.update({
                'email_to': self.commercial_id.login,
                'email_cc': ','.join(self.notify_users.mapped('email')),
                'lang': self.commercial_id.lang
            })
            template.with_context(ctx).send_mail(self.id)
        return res



class KitchenCustomizationLine(models.Model):
    _name = 'kitchen.customization.line'

    product_id = fields.Many2one('product.product', required=1)
    product_qty = fields.Float(required=1)
    customization_id = fields.Many2one('kitchen.customization', ondelete='cascade', required=True, index=True,
                                       copy=False)
    sale_line_id = fields.Many2one('sale.order.line')
    state = fields.Selection([
        ('draft', 'New'),
        ('waiting', 'Waiting Availability'),
        ('sent', 'Sent'),
        ('in_progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], related='customization_id.state', string='status', readonly=True, copy=False, store=True,
        default='draft')
    only_erase_logo = fields.Boolean()

    reserved_qty = fields.Float(compute="_compute_reserved_qty", store=True)
    type_ids = fields.Many2many('customization.type', required=1, string="Type")

    @api.depends('sale_line_id.move_ids.move_line_ids.product_id', 'sale_line_id.move_ids.move_line_ids.product_uom_id', 'sale_line_id.move_ids.move_line_ids.product_uom_qty')
    def _compute_reserved_qty(self):
        for line in self:
            line.reserved_qty = sum(line.sale_line_id.move_ids.mapped('reserved_availability')) if line.sale_line_id and line.sale_line_id.move_ids else 0

    reservation_status = fields.Selection([
        ('waiting', 'Waiting Availability'),
        ('to customize', 'Fully Reserved')
    ], string='Reservation Status', compute='_compute_reservation_status', store=True,
        default='waiting')

    @api.depends('reserved_qty')
    def _compute_reservation_status(self):
        for line in self:
            line.reservation_status="waiting"
            if line.reserved_qty >= line.product_qty and line.state == "waiting":
                line.reservation_status = "to customize"

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        if self.sale_line_id:
            customization_qty = sum([x.get("product_qty", 0) for x in
                                     self.env['kitchen.customization.line'].search_read(
                                         [('sale_line_id', '=', self.sale_line_id.id), ('state', '!=', 'cancel'),('id', '!=', self.id)],
                                         ['product_qty'])])

            if self.product_qty+customization_qty>self.sale_line_id.product_qty:
                raise exceptions.UserError(_(
                    "You cannot exceed the maximum product quantity to customize. "
                    "The maximum quantity to customize is : %s-%s unit(s)") %self.product_id.default_code,self.sale_line_id.product_qty-customization_qty)
