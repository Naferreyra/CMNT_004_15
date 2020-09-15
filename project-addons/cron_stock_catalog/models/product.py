from odoo import api, fields, models, _, exceptions
import base64
from datetime import datetime
import xlsxwriter


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def cron_stock_catalog(self):
        headers = ["ID", "Proveedor principal", "Referencia interna", "Fabricando", "Entrante", "Stock cocina",
                   "Stock real", "Stock disponible", "Ventas en los últimos 60 días con stock",
                   "Cant. pedido más grande", "Días de stock restantes", "Stock en playa",
                   "Media de margen de últimas ventas", "Cost Price", "Último precio de compra",
                   "Última fecha de compra", "Reemplazado por", "Estado"]

        domain = [('custom', '=', False), ('type', '!=', 'service'), ('seller_id.name', 'not ilike', 'outlet')]

        fields = ["id", "seller_id", "code", "qty_in_production", "incoming_qty", "qty_available_wo_wh",
                  "qty_available", "virtual_stock_conservative", "last_sixty_days_sales", "biggest_sale_qty",
                  "remaining_days_sale", "qty_available_input_loc", "average_margin",
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

        file_b64 = self.generate_xls(headers, rows)
        self.send_email(file_b64, "stock_diary",
                        "stock_catalog_{}.xlsx"
                        .format(datetime.now().strftime('%m%d')),
                        "cron_stock_catalog.email_template_purchase_stock_catalog")


    def cron_product_valuation(self):
        headers = ["ID","Nombre del Producto","Marca","Categoria","Proveedores", "Cantidad", "Valor"]

        products_real_time_ids = self.env['product.template'].search([('property_valuation', '=', 'real_time')]).ids
        domain = [('type', '=', 'product'), ('qty_available', '>', 0),
                  ('product_tmpl_id', 'in', products_real_time_ids)]

        fields = ["display_name", "qty_available", "standard_price", "cost_method", "categ_id","product_brand_id","seller_ids"]
        rows = []

        products = self.env['product.product'].with_context(company_owned=True, owner_id=False).search_read(domain,
                                                                                                            fields)
        fifo_automated_values = {}
        if products:
            self.env['account.move.line'].check_access_rights('read')
            query = """SELECT aml.product_id, aml.account_id, sum(aml.debit) -
                            sum(aml.credit)
                            FROM account_move_line AS aml
                           WHERE aml.product_id IN %%s AND aml.company_id=%%s %s
                        GROUP BY aml.product_id, aml.account_id"""
            params = (tuple(x['id'] for x in products),
                      self.env.user.company_id.id)
            query = query % ('',)
            self.env.cr.execute(query, params=params)

            res = self.env.cr.fetchall()
            for row in res:
                fifo_automated_values[(row[0], row[1])] = row[2]
        for product in products:
            value = 0
            category_name = product["categ_id"][1]
            brand_name = product["product_brand_id"][1] if product["product_brand_id"] and product["product_brand_id"][1] else 0
            if product["cost_method"] in ['standard', 'average']:
                value = round(product["standard_price"] * product["qty_available"], 2)
            elif product["cost_method"] == 'fifo':
                valuation_account_id = self.env['product.category'].browse(product["categ_id"][0]). \
                    property_stock_valuation_account_id.id
                value = round(fifo_automated_values.get((product["id"],
                                                         valuation_account_id)) or 0, 2)
            seller_ids = product["seller_ids"]
            if seller_ids:
                sellers = self.env['product.supplierinfo'].browse(seller_ids)
                display_name = sellers[0].display_name or 0
                product_fields = [product["id"],product['display_name'], brand_name, category_name,
                                  display_name, product["qty_available"], value]
                rows.append(product_fields)
                if len(sellers)>1:
                    sellers=sellers[1::]
                    for seller in sellers:
                        display_name = seller.display_name or 0
                        product_fields = ["","", "","",display_name,"",""]
                        rows.append(product_fields)
            else:
                product_fields = [product["id"],product['display_name'], brand_name, category_name,
                                  0, product["qty_available"], value]
                rows.append(product_fields)

        file_b64 = self.generate_xls(headers, rows)
        self.send_email(file_b64, "product_valuation",
                        "product_valuation_{}.xlsx".format(datetime.now().strftime('%m%d')),
                        "cron_stock_catalog.email_template_product_valuation")

    @api.multi
    def send_email(self, file, name, datas_fname, template_name):
        attach = None
        if file:
            self.env['ir.attachment'].search(
                [('res_id', '=', self.env.user.id), ('res_model', '=', 'res.users'),
                 ('name', '=', name)]).unlink()
            attach = self.env['ir.attachment'].create({
                'name': name,
                'res_model': 'res.users',
                'res_field': False,
                'res_id': self.env.user.id,
                'type': 'binary',
                'datas': file,
                'datas_fname': datas_fname,

            })
        mail_pool = self.env['mail.mail']
        context = self._context.copy()
        context['attachment'] = attach.id
        context.pop('default_state', False)

        template_id = self.env.ref(template_name)

        if template_id:
            mail_id = template_id.with_context(context).send_mail(self.id)
            if mail_id:
                mail_id_check = mail_pool.browse(mail_id)
                mail_id_check.attachment_ids = [(6, 0, [attach.id])]
                mail_id_check.with_context(context).send()

        return True

    @staticmethod
    def generate_xls(headers, rows):
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
            return base64.b64encode(file.read())

