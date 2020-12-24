from odoo import models, fields, api, exceptions, _
from odoo.tools import float_compare
import re
from datetime import datetime
from dateutil import parser
import ftplib


class EdifMenssage(models.Model):

    _name = "edif.message"

    def UNH(self, ref, typ):
        msg = "UNH+{}+{}:D:93A:UN:EAN007'\n".format(ref, typ)
        return msg

    def BGM(self, typ, ref):
        msg = "BGM+{}+{}'\n".format(typ, ref)
        return msg

    def DTM(self, typ, date):
        msg = "DTM+{}:{}:102'\n".format(typ, date)
        return msg

    def RFF(self, typ, ref):
        msg = "RFF+{}:{}'\n".format(typ, ref)
        return msg

    def NAD(self, typ, code, **kwargs):
        msg = "NAD+{}+{}::9".format(typ, code)
        if typ in ('SCO', 'BCO'):  # Razón social del Proveedor/Cliente
            name = kwargs.get('name', None)
            msg += "++{}".format(name[:35])
            msg += ":{}".format(name[35:])
            if typ == 'SCO':
                reg = kwargs.get('reg', None)
                msg += ":{}".format(reg[:35])
                msg += ":{}".format(reg[35:])
            street = kwargs.get('street', None)
            msg += "+{}".format(street)
            city = kwargs.get('city', None)
            msg += "+{}".format(city)
            pc = kwargs.get('pc', None)
            msg += "++{}".format(pc)
            msg += "+ES"
        return msg + "'\n"

    def CUX(self):
        msg = "CUX+2:EUR:4'\n"
        return msg

    def PAT(self, val):  # Forma de pago

        msg = "PAT+{}'\n".format(val)
        return msg

    def ALC(self, dc, typ):
        msg = "ALC+{}+++1+{}'\n".format(dc, typ)
        return msg

    def PCD(self, dc, perc):
        msg = "PCD"
        if dc == 'A':
            msg += "+1:{}'\n".format(perc)
        elif dc == 'C':
            msg += "+2:{}'\n".format(perc)
        return msg

    def MOA(self, typ, imp):
        msg = "MOA+{}:{}'\n".format(typ, imp)
        return msg

    def LIN(self, n, ean):
        msg = "LIN+{}++{}:EN'\n".format(n, ean)
        return msg

    def PIA(self, typ, default_code):
        msg = "PIA+{}+{}:SA'\n".format(typ, default_code)
        return msg

    def IMD(self, description):
        msg = "IMD+F+M:::{}".format(description[:35])
        if len(description) > 35:
            msg += ":{}".format(description[35:])
        return msg + "'\n"

    def QTY(self, typ, qty):
        msg = "QTY+{}:{}'\n".format(typ, qty)
        return msg

    def PRI(self, tpy, qty):
        msg = "PRI+{}:{}'\n".format(tpy, qty)
        return msg

    def TAX(self, tpy, qty):
        msg = "TAX+7+{}+++:::{}'\n".format(tpy, qty)
        return msg

    def UNS(self):
        msg = "UNS+S'\n"
        return msg

    def UNT(self, num, ref):
        msg = "UNT+{}+{}'\n".format(num, ref)
        return msg

    def generate_invoice(self, invoice):
        invoice.ensure_one()
        msg = ""
        msg_ref = "VT{}".format(datetime.now().strftime("%Y%m%d%H%M"))
        length = 35
        street_partner = invoice.partner_id.commercial_partner_id.street
        street_partner_cut = [street_partner[i:i+length] for i in range(0, len(street_partner), length)]

        msg += self.UNH(msg_ref, 'INVOIC')
        if invoice.type == 'out_invoice':
            msg += self.BGM('380', invoice.number)
        elif invoice.type == 'out_refund':
            msg += self.BGM('381', invoice.number)
        msg += self.DTM('137', invoice.date_invoice.replace("-", ""))
        msg += self.RFF('ON', invoice.name)
        for pick in invoice.picking_ids:
            msg += self.RFF('DQ', pick.name)

        # -- Interlocutors segment --
        msg += self.NAD('SU', invoice.company_id.vat[2:])
        msg += self.NAD('SCO', invoice.company_id.vat[2:],
                        name=invoice.company_id.name,
                        reg=invoice.company_id.company_registry,
                        street=invoice.company_id.street,
                        city=invoice.company_id.city,
                        pc=invoice.company_id.zip)
        msg += self.RFF('VA', self.env.user.company_id.vat)
        # msg += self.NAD('II') # Mismo que SCO
        msg += self.NAD('IV', invoice.partner_id.commercial_partner_id.ean)
        msg += self.NAD('BY', invoice.partner_shipping_id.ean)
        msg += self.NAD('DP', invoice.partner_shipping_id.ean)
        msg += self.NAD('BCO', invoice.partner_id.commercial_partner_id.ean,
                        name=invoice.partner_id.commercial_partner_id.name,
                        street=':'.join(street_partner_cut),
                        city=invoice.partner_id.commercial_partner_id.city,
                        pc=invoice.partner_id.commercial_partner_id.zip)
        msg += self.RFF('VA', invoice.partner_id.commercial_partner_id.vat)

        msg += self.CUX()
        msg += self.PAT('35')  # 35 - pago único
        msg += self.DTM('13', invoice.date_due.replace("-", ""))  # PAT

        # Estas líneas son para descuentos o cargos generales
        # msg += self.ALC()
        # msg += self.PCD()  # ALC
        # msg += self.MOA()  # ALC

        amount_discount = 0.0
        amount_net = 0.0
        for i, line in enumerate(invoice.invoice_line_ids, start=1):
            amount_line_discount = (line.quantity * line.price_unit) * (line.discount / 100)
            amount_line_net = line.quantity * line.price_unit
            amount_discount += amount_line_discount
            amount_net += amount_line_net

            msg += self.LIN(i, line.product_id.barcode or '0000000000000')
            # 1: identificacion adicional o 5: identificacion del producto
            msg += self.PIA('5', line.product_id.default_code)
            msg += self.IMD(line.name.replace("\n", " "))
            msg += self.QTY('47', str(line.quantity))
            msg += self.MOA('66', '{:.2f}'.format(line.price_subtotal))
            msg += self.PRI('AAA', str(line.price_unit))
            for tax in line.invoice_line_tax_ids:
                if tax.amount == 0.0:
                    msg += self.TAX('EXT', str(tax.amount))
                else:
                    msg += self.TAX('VAT', str(tax.amount))
                msg += self.MOA('124', str(round(line.price_subtotal * (tax.amount / 100), 2)))  # TAX
            if line.discount:
                msg += self.ALC('A', 'TD')
                msg += self.PCD('1', line.discount)  # ALC
                msg += self.MOA('8', line.quantity * line.price_unit * (line.discount/100))  # ALC

        msg += self.UNS()
        msg += self.MOA('79', str(round(amount_net, 2)))  # Importe neto
        msg += self.MOA('125', str(invoice.amount_untaxed))  # Base Imponible
        msg += self.MOA('176', str(invoice.amount_tax))  # Total impuestos
        msg += self.MOA('139', str(invoice.amount_total))  # Total a pagar
        msg += self.MOA('260', str(amount_discount))
        for tax in invoice.tax_line_ids:
            if tax.amount == 0.0:
                msg += self.TAX('EXT', str(round(tax.amount, 2)))
            else:
                msg += self.TAX('VAT', str(round(tax.amount, 2)))
            msg += self.MOA('125', str(invoice.amount_untaxed))  # TAX
            msg += self.MOA('176', str(round(invoice.amount_untaxed * (tax.amount / 100), 2)))  # TAX
        msg_count = msg.count("'") + 1
        msg += self.UNT(str(msg_count), msg_ref)

        return msg

    def parse_order(self, order_file):
        parse_errors = ""
        order_vals = {
            'state': 'reserve',
            'sale_notes': '',
            'order_line': []
        }
        line = {}
        ref_message = ""
        total_net = 0.0
        for long_segment in order_file.split("'"):
            segment = re.split("\+|:", long_segment.replace("\n", ""))
            if segment[0] == 'UNH':
                ref_message = segment[1]
                if segment[2] != 'ORDERS':
                    parse_errors += _('The message does not contain an order')
                    break
            elif segment[0] == 'BGM':
                if segment[1] == '220':
                    order_vals['client_order_ref'] = segment[2]
            elif segment[0] == 'DTM':
                if segment[1] == '137':
                    order_vals['date_order'] = datetime.strptime(segment[2], '%Y%m%d')
                if segment[1] == '2':
                    order_vals['sale_notes'] += 'FECHA DE ENTREGA: {} \n'.format(datetime.strptime(segment[2], '%Y%m%d').
                                                                              strftime("%d/%m/%Y"))
            elif segment[0] == 'FTX':
                if segment[1] == 'AAI':
                    order_vals['sale_notes'] += ''.join(segment[4:len(segment)])
            elif segment[0] == 'NAD':
                if segment[1] == 'DP':
                    partner_ship = self.env['res.partner'].search([('ean', '=', segment[2])])
                    if not partner_ship:
                        parse_errors += _('The partner {} does not exist').format(segment[2])
                        break
                    else:
                        order_vals['partner_id'] = partner_ship.commercial_partner_id.id
                        order_vals['partner_shipping_id'] = partner_ship.id
                        exist_order = self.env['sale.order'].search([('partner_id.id', '=', order_vals['partner_id']),
                                                                     ('client_order_ref', '=', order_vals['client_order_ref'])])
                        if exist_order:
                            parse_errors += _('The order is already created')
                            break
            elif segment[0] == 'RFF':
                pass
            elif segment[0] == 'TOD':
                pass
            elif segment[0] == 'LIN':
                if line:
                    order_vals['order_line'].append((0, 0, line))
                line = {'sequence': int(segment[1])}
                product = self.env['product.product'].search([('barcode', '=', segment[3])])
                if len(product) > 1:
                    parse_errors += _('More than one product with EAN {}').format(segment[3])
                    break
                if product:
                    line['product_id'] = product.id
                else:
                    parse_errors += _('Product with EAN {} not found').format(segment[3])
                    break
            elif segment[0] == 'PIA':
                pass
            elif segment[0] == 'IMD':
                pass
            elif segment[0] == 'QTY':
                if segment[1] == '21':
                    line['product_uom_qty'] = int(segment[2])
            elif segment[0] == 'MOA':
                if segment[1] == '79':  # Total neto
                    if float_compare(total_net, float(segment[2]), precision_digits=2) != 0:
                        parse_errors += _('The total net price does not match with the sum of the lines')
                        break
                elif segment[1] == '66':  # Subtotal
                    total_net += float(segment[2])
            elif segment[0] == 'PRI':
                if segment[1] == 'AAA':  # Precio Neto línea
                    line['price_unit'] = float(segment[2])
            elif segment[0] == 'ALC':
                pass
            elif segment[0] == 'UNS':  # Final de las líneas
                if line:
                    order_vals['order_line'].append((0, 0, line))
            elif segment[0] == 'UNT':
                if ref_message != segment[2]:
                    parse_errors += _('Message identifier does not match')
                    break

        order_vals['no_promos'] = True
        if not parse_errors:
            shipping_prod = self.env['product.product'].search([('default_code', '=', 'GASTOS DE ENVIO')])
            sale = self.env['sale.order'].create(order_vals)
            if sale:
                shipping_vals = {
                    'product_id': shipping_prod.id,
                    'name': shipping_prod.default_code,
                    'product_uom_qty': 1,
                    'product_uom': 1,
                    'price_unit': 7,
                    'discount': 100,
                    'order_id': sale.id
                }
                self.env['sale.order.line'].create(shipping_vals)
                sale.onchange_partner_id()
                sale.write({'partner_shipping_id': order_vals['partner_shipping_id']})
                sale.apply_commercial_rules()

        return parse_errors


class EdifFile(models.Model):

    _name = "edif.file"
    _order = "read_date desc"

    file_name = fields.Char(string='File')
    read_date = fields.Datetime(string='Read date')
    error = fields.Char(string='Error')

    @api.model
    def search_for_orders(self):

        ftp_dir = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_dir')
        ftp_user = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_user')
        ftp_pass = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_pass')
        ftp_folder = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_folder')

        # FTP login and place
        ftp = ftplib.FTP(ftp_dir)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        ftp.cwd(ftp_folder)

        # Read the files
        files = []
        lines = []
        latest_date = False
        ftp.dir("", lines.append)  # Read every line in the folder
        date_reading = fields.Datetime.now()
        latest_date_str = self.search([], limit=1, order='read_date desc').read_date

        for line in lines:  # Get the latest files only
            pieces = line.split(maxsplit=9)
            datetime_str = pieces[5] + " " + pieces[6] + " " + pieces[7]
            line_datetime = parser.parse(datetime_str)
            if latest_date_str:
                latest_date = parser.parse(latest_date_str)
            if line_datetime > latest_date:
                files.append(pieces[8])

        for file in files:
            vals = {
                'file_name': file,
                'read_date': date_reading,
                'error': False
            }
            created_file = self.create(vals)
            ftp.retrbinary("RETR %s" % file, callback=created_file.decode_file)

        ftp.quit()

    @api.multi
    def decode_file(self, data):
        order_file = data.decode('latin-1')
        message_obj = self.env['edif.message']
        self.error = False
        errors = message_obj.parse_order(order_file)
        self.error = errors
        if errors or errors != '':
            self.send_error_mail()

    @api.multi
    def retry_file(self):
        for file in self:
            ftp_dir = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_dir')
            ftp_user = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_user')
            ftp_pass = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_pass')
            ftp_folder = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_folder')

            # FTP login and place
            ftp = ftplib.FTP(ftp_dir)
            ftp.login(user=ftp_user, passwd=ftp_pass)
            ftp.cwd(ftp_folder)

            ftp.retrbinary("RETR %s" % file.file_name, callback=file.decode_file)

            ftp.quit()

    @api.multi
    def send_error_mail(self):
        mail_pool = self.env['mail.mail']
        context = self._context.copy()
        context.pop('default_state', False)

        template_id = self.env.ref('edi_edifact.email_template_edi_read_error')

        if template_id:
            mail_id = template_id.with_context(context).send_mail(self.id)
            if mail_id:
                mail_id_check = mail_pool.browse(mail_id)
                mail_id_check.with_context(context).send()

        return True
