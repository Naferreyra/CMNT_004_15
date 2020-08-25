from odoo import api, fields, models, _, exceptions
import base64
from datetime import datetime
import xlsxwriter


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def cron_stock_catalog(self):
        headers = ["ID", "Proveedor principal", "Referencia interna", "Fabricando", "Entrante", "Stock cocina",
                   "Stock real", "Stock disponible", "Ventas en los últimos 60 días con stock",
                   "Cant. pedido más grande", "Días de stock restantes", "Stock en playa", "Stock alm. externo",
                   "Media de margen de últimas ventas", "Cost Price", "Último precio de compra",
                   "Última fecha de compra", "Reemplazado por", "Estado"]

        domain = [('custom', '=', False), ('type', '!=', 'service'), ('seller_id.name', 'not ilike', 'outlet')]

        fields = ["id", "seller_id", "code", "qty_in_production", "incoming_qty", "qty_available_wo_wh",
                  "qty_available", "virtual_stock_conservative", "last_sixty_days_sales", "biggest_sale_qty",
                  "remaining_days_sale", "qty_available_input_loc", "qty_available_external", "average_margin",
                  "standard_price", "last_purchase_price", "last_purchase_date", "replacement_id", "state"]
        rows = []
        translate_state = {"draft": "En desarrollo", "sellable": "Normal", "end": "Fin del ciclo de vida",
                           "obsolete": "Obsoleto", "make_to_order": "Bajo pedido"}

        products = self.env['product.product'].search_read(domain, fields)
        for product in products:
            product_fields = []
            for field in fields:
                if product[field] is False:
                    product_fields.append("")
                elif field in ('seller_id', 'replacement_id'):
                    product_fields.append(product[field][1])
                elif field == 'state':
                    product_fields.append(translate_state[product[field]])
                elif field == 'average_margin':
                    product_fields.append(round(product[field], 2))
                else:
                    product_fields.append(product[field])
            rows.append(product_fields)

        # Generate the xls
        file_name = 'temp'
        workbook = xlsxwriter.Workbook(file_name, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        row = 0
        col = 0
        for e in headers:
            worksheet.write(row, col, e)
            col += 1
        row += 1
        for data_row in rows:
            col = 0
            for cell in data_row:
                worksheet.write(row, col, cell)
                col += 1
            row += 1
        workbook.close()

        with open(file_name, "rb") as file:
            file_b64 = base64.b64encode(file.read())

        self.send_stock_email(file_b64)

    @api.multi
    def send_stock_email(self, file):
        attach = None
        if file:
            self.env['ir.attachment'].search(
                [('res_id', '=', self.env.user.id), ('res_model', '=', 'res.users'),
                 ('name', '=', 'stock_diary')]).unlink()
            attach = self.env['ir.attachment'].create({
                'name': "stock_diary",
                'res_model': 'res.users',
                'res_field': False,
                'res_id': self.env.user.id,
                'type': 'binary',
                'datas': file,
                'datas_fname': "stock_catalog_{}.xlsx"
                .format(datetime.now().strftime('%m%d')),

            })
        mail_pool = self.env['mail.mail']
        context = self._context.copy()
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
