from odoo import models, fields, _, exceptions, api


class KitchenCustomization(models.Model):
    _name = 'kitchen.customization'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('commercial_id')
    def _compute_is_manager(self):
        self.is_manager = self.env.user.has_group('kitchen.group_kitchen')

    is_manager = fields.Boolean(compute='_compute_is_manager', default=True)
    name = fields.Char(default='New', readonly=True, string="Name")
    order_id = fields.Many2one('sale.order', string="Order", domain=[('state', '=', 'reserve'),('customization_count_not_cancelled','=',0)])
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

    date_planned = fields.Datetime()
    comments = fields.Text(string='Comments')
    order_state = fields.Selection(related='order_id.state')

    def _compute_products_format(self):
        for customization in self:
            customization.products_qty_format = ""
            for line in customization.customization_line:
                only_logo = _("(ERASE LOGO)") if line.erase_logo else ""
                types = line.type_ids.mapped('name')
                customization.products_qty_format += ' %i * %s %s %s;\n' % (
                line.product_qty, line.product_id.default_code, types, only_logo)

    products_qty_format = fields.Char(compute="_compute_products_format")

    def action_done(self):
        self.state = 'done'
        if self.customization_line and self.customization_line[0].move_ids:
            picking = self.customization_line[0].move_ids[0].picking_id
            if picking:
                picking.write({'not_sync': False})
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
        if any(self.customization_line.filtered(lambda l: l.product_qty <= 0)):
            raise exceptions.UserError(
                _("You can't create a customization with a quantity of less than one of a product"))
        lines_without_type = self.customization_line.filtered(lambda l: not l.type_ids)
        if lines_without_type:
            raise exceptions.UserError(
                _("You can't confirm a customization without a customization type: %s") % lines_without_type.mapped(
                    'product_id.default_code'))
        if self.order_id:
            customization_product_lines = set(self.customization_line.mapped('product_id.default_code'))
            order_product_lines = set(self.order_id.order_line.mapped('product_id.default_code'))
            if not customization_product_lines.issubset(order_product_lines):
                raise exceptions.UserError(
                    _("You can't confirm a customization with products that not belong to the original order: %s") % str(
                        customization_product_lines - order_product_lines))
        self.write({'state': 'sent'})
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
            order_id = self.env['sale.order'].browse(vals.get('order_id'))
            if order_id.customization_count != 0 and not vals.get('backorder_id',False):
                raise exceptions.UserError(_("You cannot create a new customization because the selected order already "
                                             "has one, please cancel it before creating a new one"))
            order_id.message_post(
                body=_("The order contains customized products"))
        if vals.get("customization_line", False):
            for line in vals.get("customization_line", False):
                line = line[2]
                if line and (not line.get("type_ids", False) or not line.get("type_ids", False)[0][2]):
                    raise exceptions.UserError(
                        _("You can't save a customization without a customization type: %s")
                        % self.env['product.product'].browse(line.get("product_id")).default_code)
        return super(KitchenCustomization, self).create(vals)

    @api.multi
    def action_cancel(self):
        for customization in self:
            if customization.state in ['done', 'in_progress']:
                if not self.env.user.has_group('kitchen.group_kitchen'):
                    raise exceptions.UserError(
                        _("You can't cancel an active customization. Please, contact the kitchen staff."))
            elif customization.order_id and customization.state == 'sent':
                picking = customization.customization_line[0].move_ids[0].picking_id \
                    if customization.customization_line and customization.customization_line[0].move_ids else False
                if picking:
                    picking.write({'not_sync': False})
            customization.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'

    @api.onchange('order_id')
    def onchange_order_id(self):
        if self.order_id:
            self.partner_id = self.order_id.partner_id
            self.commercial_id = self.order_id.user_id
            self.notify_users = [(6, 0, [self.order_id.user_id.id])]
            self.customization_line = False
            for line in self.order_id.order_line.filtered(
                    lambda l: not l.deposit and l.product_id.categ_id.with_context(
                        lang='es_ES').name != 'Portes' and l.price_unit >= 0):
                customization_qty = sum([x.get("product_qty", 0) for x in
                                         self.env['kitchen.customization.line'].search_read(
                                             [('sale_line_id', '=', line.id), ('state', '!=', 'cancel')],
                                             ['product_qty'])])
                if line.product_qty - customization_qty > 0:
                    new_line = {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty - customization_qty,
                        'sale_line_id': line.id,
                        'customization_id': self.id
                    }
                    self.customization_line.new(new_line)

    @api.multi
    def create_backorder_customization(self,backorder_moves):
        new_customization = self.copy({
                        'name': '/',
                        'customization_line': [],
                        'backorder_id': self.id,
                        'state': 'waiting'
            })
        new_lines = self.env['kitchen.customization.line']
        for move in backorder_moves:
            if move.customization_line.product_qty > move.product_uom_qty:
                move.customization_line.product_qty-=move.product_uom_qty
                new_line = move.customization_line.copy(
                    {'product_qty': move.product_uom_qty, 'move_ids': [(6, 0, [move.id])]})
                new_lines += new_line
            else:
                new_lines += move.customization_line

        if new_customization and new_lines:
            new_lines.write({'customization_id':new_customization.id})



    def write(self, vals):
        lines_without_type = self.customization_line.filtered(lambda l: not l.type_ids)
        if lines_without_type and not vals.get("customization_line", False):
            raise exceptions.UserError(
                _("You can't save a customization without a customization type: %s") % lines_without_type.mapped(
                    'product_id.default_code'))
        if vals.get("order_id", False):
            order_id = self.env['sale.order'].browse(vals.get('order_id'))
            if order_id.customization_count != 0 and not vals.get('backorder_id',False):
                raise exceptions.UserError(_("You cannot create a new customization because the selected order already "
                                             "has one, please cancel it before creating a new one"))

        if vals.get("customization_line", False):
            for line in vals.get("customization_line", False):
                line = line[2]
                if line and (not line.get("type_ids", False) or not line.get("type_ids", False)[0][2]):
                    raise exceptions.UserError(_("You can't save a customization without a customization type: %s")
                        % self.env['product.product'].browse(line.get("product_id")).default_code)

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

    reservation_status = fields.Selection([
        ('waiting', 'Waiting Availability'),
        ('to customize', 'Fully Reserved')
    ], string='Reservation Status', compute='_compute_reservation_status', store=True, default='to customize')

    @api.depends('customization_line.reservation_status')
    def _compute_reservation_status(self):
        for customization in self:
            customization.reservation_status = "waiting"
            if customization.customization_line and all(
                    [x.reservation_status and x.reservation_status != "waiting" for x in customization.customization_line]):
                if not customization.order_id or customization.order_id.state=='sale':
                    customization.action_confirm()
                customization.reservation_status = "to customize"



    backorder_id = fields.Many2one('kitchen.customization', ondelete='cascade')


class KitchenCustomizationLine(models.Model):
    _name = 'kitchen.customization.line'

    product_id = fields.Many2one('product.product', required=1)
    product_qty = fields.Float(required=1)
    customization_id = fields.Many2one('kitchen.customization', ondelete='cascade', index=True,
                                       copy=False)
    sale_line_id = fields.Many2one('sale.order.line')
    state = fields.Selection([
        ('draft', 'New'),
        ('waiting','Waiting Availability'),
        ('sent', 'Sent'),
        ('in_progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], related='customization_id.state', string='status', readonly=True, copy=False, store=True,
        default='draft')
    erase_logo = fields.Boolean()

    type_ids = fields.Many2many('customization.type', required=1, string="Type")

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        if self.sale_line_id:
            domain = [('sale_line_id', '=', self.sale_line_id.id), ('state', '!=', 'cancel'),
                      ('id', '!=', self._origin.id)]
            customization_qty = sum([x.get("product_qty", 0) for x in
                                     self.env['kitchen.customization.line'].search_read(domain, ['product_qty'])])

            if self.product_qty + customization_qty > self.sale_line_id.product_qty:
                raise exceptions.UserError(
                    _("You cannot exceed the maximum product quantity to customize. The maximum quantity to customize is : %s-%i unit(s)")
                    % (self.product_id.default_code, (self.sale_line_id.product_qty - customization_qty)))
        if self.product_qty < 0:
            raise exceptions.UserError(_("You cannot change the product quantity to less than 0"))

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id and self.customization_id and self.customization_id.order_id:
            line = self.env['sale.order.line'].search(
                [('product_id', '=', self.product_id.id), ('order_id', '=', self.customization_id.order_id.id)])
            if not line:
                raise exceptions.UserError(_("you cannot select a product (%s) that is not in the order %s")
                    % (self.product_id.default_code, self.customization_id.order_id.name))
            self.sale_line_id = line.id
            self.onchange_product_qty()

    reserved_qty = fields.Float(compute="_compute_reserved_qty", store=True)

    @api.depends('move_ids.move_line_ids.product_id', 'move_ids.move_line_ids.product_uom_id',
                 'move_ids.move_line_ids.product_uom_qty', 'move_ids')
    def _compute_reserved_qty(self):
        for line in self:
            line.reserved_qty = sum(line.move_ids.mapped(
                'reserved_availability')) if line.move_ids else 0

    reservation_status = fields.Selection([
        ('waiting', 'Waiting Availability'),
        ('to customize', 'Fully Reserved')
    ], string='Reservation Status', compute='_compute_reservation_status', store=True,
        default='waiting')

    @api.depends('reserved_qty')
    def _compute_reservation_status(self):
        for line in self:
            line.reservation_status = "waiting"
            if line.reserved_qty >= line.product_qty and line.state in ('waiting','draft'):
                line.reservation_status = "to customize"

    move_ids = fields.One2many('stock.move','customization_line')
