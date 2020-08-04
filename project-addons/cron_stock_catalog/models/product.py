from odoo import api, fields, models, _, exceptions
import csv
import io
import base64


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def cron_stock_catalog(self):
        headers = ["ID", "Proveedor principal", "Referencia interna", "Fabricando", "Entrante", "Stock cocina",
                   "Stock real", "Stock disponible", "Ventas en los últimos 60 dias con stock",
                   "Cant. pedido mas grande", "Dias de stock restantes", "Stock en playa", "Stock alm. externo",
                   "Media de margen de ultimas ventas", "Cost Price", "Ultimo precio de compra",
                   "Ultima fecha de compra", "Reemplazado por", "Estado"]

        domain = [('custom', '=', False), ('type', '!=', 'service'), ('seller_id.name', 'not ilike', 'outlet')]
        fields = ["id", "seller_id", "code", "qty_in_production", "incoming_qty", "qty_available_wo_wh",
                  "qty_available", "virtual_stock_conservative", "last_sixty_days_sales", "biggest_sale_qty",
                  "remaining_days_sale", "qty_available_input_loc", "qty_available_external", "average_margin",
                  "standard_price", "last_purchase_price", "last_purchase_date", "replacement_id", "state"]
        rows = []

        products = self.env['product.product'].search_read(domain, fields, limit=2)
        for product in products:
            product_fields = []
            for field in fields:
                if field == 'seller_id':
                    product_fields.append(product[field][1])
                else:
                    if product[field] is False:
                        product_fields.append("")
                    else:
                        product_fields.append(product[field])
            rows.append(product_fields)

        # Create the csv
        s = io.StringIO()
        csv.writer(s).writerow(headers)
        csv.writer(s).writerows(rows)
        s.seek(0)
        buf = io.BytesIO()
        buf.write(s.getvalue().encode())
        buf.seek(0)
        buf.name = 'stock_catalog.csv'

        self.send_stock_email(buf)


    @api.multi
    def send_stock_email(self, file):
        attach = None
        if file:
            attach = self.env['ir.attachment'].create({
                'name': "stock_diary",
                'res_model': 'res.users',
                'res_field': False,
                'res_id': 1,
                'type': 'binary',
                'datas': base64.b64encode(file.read()),
                'datas_fname': "stock_catalog.csv",

            })
        mail_pool = self.env['mail.mail']
        context = self._context.copy()
        context['base_url'] = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        context['attachment'] = attach.id
        context.pop('default_state', False)

        template_id = self.env.ref('cron_stock_catalog.email_template_purchase_stock_catalog')

        if template_id:
            mail_id = template_id.with_context(context).send_mail(self.id)
            if mail_id:
                mail_id_check = mail_pool.browse(mail_id)
                mail_id_check.attachment_ids = [(6, 0, [attach.id])]
                mail_id_check.with_context(context).send()

        return True
