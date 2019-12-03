import werkzeug
import phonenumbers
from odoo import http, exceptions,_
from odoo.http import request, route, Response


class PhoneController(http.Controller):

    @http.route('/phone_redirect', type='http', auth="user")
    def phone_redirect(self, phone):
        if len(phone) <= 3:
            raise werkzeug.exceptions.abort(
                Response(_("Odoo could not load due to the caller phone number is an internal number")))

        phone = str(int(phone))
        valid_try = True
        try:
            phone_parsed = phonenumbers.parse("+" + phone, None)
            if not phonenumbers.is_valid_number(phone_parsed):
                valid_try = False
                raise exceptions.Warning("The number is not an international phone number")
        except:
            country_code_phone = request.env['ir.config_parameter'].sudo().get_param('country_code_phone')
            phone_parsed = phonenumbers.parse(country_code_phone + phone, None)
        finally:
            if valid_try or phonenumbers.is_valid_number(phone_parsed):
                phone_formatted = phonenumbers.format_number(phone_parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                phone = str(phone_parsed.national_number)
                partners = request.env['res.partner'].search(
                    ['|', '|', '|', ('phone', 'ilike', phone_formatted), ('phone', 'like', phone),
                     ('mobile', 'ilike', phone_formatted), ('mobile', 'like', phone)])
                if partners:
                    if len(partners) > 1:
                        partners = [partner for partner in partners if not partner.parent_id]
                    if partners[0].parent_id:
                        partner = partners[0].parent_id
                    else:
                        partner = partners[0]
                    record_url = '/web/?#id=' + str(partner.id) + '&view_type=form&model=res.partner'
                else:
                    record_url = 'web#view_type=list&model=res.partner&menu_id=1489&action=60'
            else:
                record_url = 'web#view_type=list&model=res.partner&menu_id=1489&action=60'
            return werkzeug.utils.redirect(record_url)
