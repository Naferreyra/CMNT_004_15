##############################################################################
#
#    Author: Jesus Garcia Manzanas
#    Copyright 2018 Visiotech
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
import json
import re
import ast
import base64
import unidecode
import collections

import time

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def compute_variables(self):
        view_id = self.env['picking.rated.wizard']
        new = view_id.create({})
        data_list = self.env['picking.rated.wizard.tree']
        content = data_list.search([('order_id', '=', self.id)])
        message_error = ""
        if content:
            content.unlink()
        for order in self:
            shipment_groups = order.env['res.country.group'].search([('shipment', '=', True),
                                                                     ('country_ids', 'in', order.partner_shipping_id.country_id.id)])
            transporter_ids = order.env['transportation.transporter'].search([('country_group_id', 'in', shipment_groups.ids)])

            package_weight = 0.0
            package_pieces = 0
            products_wo_weight = 0
            products_without_weight = ''
            for order_line in order.order_line:
                if order_line.product_id.weight == 0 and order_line.product_id.type == 'product':
                    products_wo_weight += 1
                    products_without_weight = products_without_weight + ' %s' % (order_line.product_id.default_code)
                    continue
                package_weight += float(order_line.product_id.weight * order_line.product_uom_qty)
                package_pieces += int(order_line.product_uom_qty)
            num_pieces = int((package_weight / 20) + 1)
            package_weight = str(round(package_weight, 2))
            products_wo_weight = str(products_wo_weight)
            if products_wo_weight != '0':
                products_wo_weight = products_wo_weight +\
                                     " of the product(s) of the order don't have set the weights," +\
                                     " please take the shipping cost as an aproximation"
            new.write({'total_weight': package_weight,
                       'products_wo_weight': products_wo_weight,
                       'products_without_weight': products_without_weight})
            for transporter in transporter_ids:
                if transporter.name == 'UPS':
                    service_codes = ast.literal_eval(order.env['ir.config_parameter'].sudo().get_param('service.codes.ups.api.request'))
                    user_id = order.env['ir.config_parameter'].sudo().get_param('user.ups.api.request')
                    password_id = order.env['ir.config_parameter'].sudo().get_param('password.ups.api.request')
                    access_id = order.env['ir.config_parameter'].sudo().get_param('access.ups.api.request')
                    shipper_number = order.env['ir.config_parameter'].sudo().get_param('shipper.number.ups.api.request')

                    shipper_name = "Visiotech"
                    shipper = order.env['res.company'].browse(1).partner_id
                    shipper_address_line = shipper.street
                    shipper_city = shipper.city
                    shipper_province_code = shipper.state_id.code
                    shipper_postal_code = shipper.zip
                    shipper_country_code = shipper.country_id.code

                    ship_to_name = order.partner_id.name
                    ship_to_address_line_1 = order.partner_shipping_id.street
                    ship_to_address_line_2 = order.partner_shipping_id.street2 if order.partner_shipping_id.street2 else ''
                    ship_to_city = order.partner_shipping_id.city
                    ship_to_province_code = order.partner_shipping_id.state_id.code
                    ship_to_postal_code = order.partner_shipping_id.zip
                    ship_to_country_code = order.partner_shipping_id.country_id.code

                    ship_from_name = shipper_name
                    ship_from_address_line = shipper.street
                    ship_from_city = shipper.city
                    ship_from_province_code = shipper.state_id.code
                    ship_from_postal_code = shipper.zip
                    ship_from_country_code = shipper.country_id.code

                    dimension_measure_code = 'CM'
                    dimension_measure_description = 'Centimeters'
                    weight_measure_code = 'KGS'
                    weight_measure_description = 'Kilogrames'

                    package_length = 10
                    package_width = 10
                    package_height = 10
                    context = ""

                    for service in transporter.service_ids:
                        service_code = service_codes[service.name]
                        rate_request = {
                            "UPSSecurity": {
                                "UsernameToken": {
                                    "Username":  user_id,
                                    "Password": password_id
                                },
                                "ServiceAccessToken": {
                                    "AccessLicenseNumber": access_id
                                }
                            },
                            "RateRequest": {
                                "Request": {
                                    "RequestOption": "Rate",
                                    "TransactionReference": {
                                        "CustomerContext": context
                                    }
                                },
                                "Shipment": {
                                    "Shipper": {
                                        "Name": shipper_name,
                                        "ShipperNumber": shipper_number,
                                        "Address": {
                                            "AddressLine": [shipper_address_line],
                                            "City": shipper_city,
                                            "StateProvinceCode": shipper_province_code,
                                            "PostalCode": shipper_postal_code,
                                            "CountryCode": shipper_country_code
                                        }
                                    },
                                    "ShipTo": {
                                        "Name": ship_to_name,
                                        "Address": {
                                            "AddressLine": [ship_to_address_line_1, ship_to_address_line_2],
                                            "City": ship_to_city,
                                            "StateProvinceCode": ship_to_province_code,
                                            "PostalCode": ship_to_postal_code,
                                            "CountryCode": ship_to_country_code
                                        }
                                    },
                                    "ShipFrom": {
                                        "Name": ship_from_name,
                                        "Address": {
                                            "AddressLine": [ship_from_address_line],
                                            "City": ship_from_city,
                                            "StateProvinceCode": ship_from_province_code,
                                            "PostalCode": ship_from_postal_code,
                                            "CountryCode": ship_from_country_code
                                        }
                                    },
                                    "Service": {
                                        "Code": service_code,
                                        "Description": "Service Code Description"
                                    },
                                    "Package": [],
                                    "ShipmentRatingOptions": {
                                        "NegotiatedRatesIndicator": "1"
                                    }
                                }
                            }
                        }

                        # Generate multiple packages
                        package_w = 0.0
                        for p in range(int(float(package_weight)/30)+1):
                            package_w = package_w + 30
                            if float(package_weight) - package_w > 0:
                                rate_request['RateRequest']['Shipment']['Package'].append({
                                                "PackagingType": {
                                                    "Code": "02",
                                                    "Description": "Rate"
                                                },
                                                "Dimensions": {
                                                    "UnitOfMeasurement": {
                                                        "Code": dimension_measure_code,
                                                        "Description": dimension_measure_description
                                                    },
                                                    "Length": str(package_length),
                                                    "Width": str(package_width),
                                                    "Height": str(package_height)
                                                },
                                                "PackageWeight": {
                                                    "UnitOfMeasurement": {
                                                        "Code": weight_measure_code,
                                                        "Description": weight_measure_description
                                                    },
                                                    "Weight": "30.0"
                                                }
                                            })
                            elif float(package_weight) - package_w < 0:
                                rate_request['RateRequest']['Shipment']['Package'].append({
                                    "PackagingType": {
                                        "Code": "02",
                                        "Description": "Rate"
                                    },
                                    "Dimensions": {
                                        "UnitOfMeasurement": {
                                            "Code": dimension_measure_code,
                                            "Description": dimension_measure_description
                                        },
                                        "Length": str(package_length),
                                        "Width": str(package_width),
                                        "Height": str(package_height)
                                    },
                                    "PackageWeight": {
                                        "UnitOfMeasurement": {
                                            "Code": weight_measure_code,
                                            "Description": weight_measure_description
                                        },
                                        "Weight": str(float(package_weight) - p * 30)
                                    }
                                })
                            elif float(package_weight) - package_w == 0:
                                rate_request['RateRequest']['Shipment']['Package'].append({
                                    "PackagingType": {
                                        "Code": "02",
                                        "Description": "Rate"
                                    },
                                    "Dimensions": {
                                        "UnitOfMeasurement": {
                                            "Code": dimension_measure_code,
                                            "Description": dimension_measure_description
                                        },
                                        "Length": str(package_length),
                                        "Width": str(package_width),
                                        "Height": str(package_height)
                                    },
                                    "PackageWeight": {
                                        "UnitOfMeasurement": {
                                            "Code": weight_measure_code,
                                            "Description": weight_measure_description
                                        },
                                        "Weight": "30.0"
                                    }
                                })
                                break

                        url = order.env['ir.config_parameter'].sudo().get_param('url.prod.ups.api.request')
                        json_request = rate_request
                        try:
                            response = requests.session().post(url, data=json.dumps(json_request),timeout=5)
                        except (requests.exceptions.ConnectionError,requests.exceptions.Timeout) as e:
                            message_error += "UPS: Connection error on UPS webpage. %s \n" % e
                            break

                        if response.status_code != 200:
                            message_error += "UPS: "+ response.text+" \n"
                            continue
                        if 'error' in response.url:
                            message_error += "UPS: Could not find information on url '%s' \n" % response.url
                            continue

                        info = json.loads(response.text)

                        if "RateResponse" in info:
                            data = info["RateResponse"]["RatedShipment"]["NegotiatedRateCharges"]
                            if data:
                                currency = data['TotalCharge']['CurrencyCode']
                                amount = data['TotalCharge']['MonetaryValue']
                                rated_status = {
                                    'currency': currency,
                                    'amount': amount,
                                    'service': service.name,
                                    'order_id': order.id,
                                    'wizard_id': new.id
                                }
                                new.write({'data': [(0, 0, rated_status)]})

                elif transporter.name == 'SEUR':
                    account_code = order.env['ir.config_parameter'].sudo().get_param('account.code.seur.api.request')
                    user_id = order.env['ir.config_parameter'].sudo().get_param('user.seur.api.request')
                    password_id = order.env['ir.config_parameter'].sudo().get_param('password.seur.api.request')
                    destination_city = order.partner_shipping_id.city
                    destination_postal_code = order.partner_shipping_id.zip
                    url = order.env['ir.config_parameter'].sudo().get_param('url.seur.api.request')
                    list_services = ast.literal_eval(order.env['ir.config_parameter'].sudo().get_param('services.seur.api.request'))
                    list_products = order.env['ir.config_parameter'].sudo().get_param('products.seur.api.request')

                    for service_id, service_name in list_services.items():
                        service_code = service_id
                        language_code = "ES"
                        headers = {'content-type': 'text/xml'}
                        template = ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ecat="http://eCatalogoWS">'
                                       '<soapenv:Header/>'
                                       '<soapenv:Body>'
                                          '<ecat:tarificacionPrivadaStr>'
                                             '<ecat:in0>'
                                    '<![CDATA['
                                    '<REG>'
                                    '<USUARIO>' + str(user_id) + '</USUARIO>'
                                    '<PASSWORD>' + str(password_id) + '</PASSWORD>'
                                    '<NOM_POBLA_DEST>' + str(destination_city) + '</NOM_POBLA_DEST>'
                                    '<Peso>' + str(package_weight) + '</Peso>'
                                    '<C0DIGO_POSTAL_DEST>' + str(destination_postal_code) + '</C0DIGO_POSTAL_DEST>'
                                    '<CodContableRemitente>' + str(account_code) + '</CodContableRemitente>'
                                    '<PesoVolumen>0.001</PesoVolumen>'
                                    '<Bultos>' + str(num_pieces) + '</Bultos>'
                                    '<CodServ>' + str(service_code) + '</CodServ>'
                                    '<CodProd>' + str(list_products) + '</CodProd>'
                                    '<COD_IDIOMA>' + str(language_code) + '</COD_IDIOMA>'
                                    '</REG>'
                                    ']]>'
                                        '</ecat:in0>'
                                          '</ecat:tarificacionPrivadaStr>'
                                       '</soapenv:Body>'
                                    '</soapenv:Envelope>')

                        try:
                            response = requests.session().post(url, data=template, headers=headers,timeout=5)
                        except (requests.exceptions.ConnectionError,requests.exceptions.Timeout) as e:
                            message_error += "SEUR: Connection error on SEUR webpage %s \n" % e
                            break
                        if response.status_code != 200:
                            message_error += "SEUR: %s \n" % response.text
                            continue
                        if 'error' in response.url:
                            message_error += "SEUR: Could not find information on url '%s' \n" % response.url
                            continue
                        response_data = response.text
                        concept_codes_valids = ['10', '75']
                        if '&gt;' in response.text:
                            response_data = response_data.replace('&gt;', '>')
                        if '&lt;' in response.text:
                            response_data = response_data.replace('&lt;', '<')
                        if 'encoding=' in response.text:
                            response_data = re.sub('(<\?xml(.+?)>)', '', response_data)
                        if 'ns1:out' in response.text:
                            response_data = re.sub('.+<ns1:out>', '', response_data)
                            response_data = re.sub('<\/ns1:out>.+', '', response_data)
                        try:
                            shipping_amount = 0.0
                            response_data = '<?xml version="1.0" encoding="utf-8"?>' + response_data
                            root = ET.fromstring(response_data.encode('UTF-8'))
                            for children in root.iter('REG'):
                                for code in children.iterfind('COD_CONCEPTO_IMP'):
                                    if code.text in concept_codes_valids:
                                        for value in children.iterfind('VALOR'):
                                            shipping_amount += float(value.text)
                        except AttributeError:
                            message_error += "SEUR: The response is not valid or it changed \n"
                            continue

                        if shipping_amount:
                            currency = "EUR"
                            rated_status = {
                                'currency': currency,
                                'amount': shipping_amount,
                                'service': service_name,
                                'order_id': order.id,
                                'wizard_id': new.id
                            }
                            new.write({'data': [(0, 0, rated_status)]})

                elif transporter.name == 'TNT':
                    service_codes = ast.literal_eval(order.env['ir.config_parameter'].sudo().get_param('service.codes.tnt.api.request'))
                    account_number = order.env['ir.config_parameter'].sudo().get_param('account.number.tnt.api.request')
                    account_country = order.env['ir.config_parameter'].sudo().get_param('account.country.tnt.api.request')
                    #account_user_test = order.env['ir.config_parameter'].sudo().get_param('account.user.test.tnt.api.request')
                    account_user = order.env['ir.config_parameter'].sudo().get_param('account.user.tnt.api.request')
                    #account_password_test = order.env['ir.config_parameter'].sudo().get_param('account.password.test.tnt.api.request')
                    account_password = order.env['ir.config_parameter'].sudo().get_param('account.password.tnt.api.request')
                    url = order.env['ir.config_parameter'].sudo().get_param('url.tnt.api.request')

                    sender = order.env['res.company'].browse(1).partner_id
                    sender_country = sender.country_id.code
                    sender_town = sender.city
                    sender_postcode = sender.zip

                    delivery_town = order.partner_shipping_id.city
                    delivery_postcode = order.partner_shipping_id.zip
                    delivery_country = order.partner_shipping_id.country_id.code

                    auth = str(account_user) + ":" + str(account_password)
                    auth = auth.encode("utf-8")
                    byte_auth = bytearray(auth)
                    authentication = base64.b64encode(byte_auth).decode("utf-8")
                    headers = {'content-type': 'text/xml', 'Authorization': 'Basic %s' % str(authentication)}
                    now = datetime.now()
                    rate_request = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <priceRequest xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                        <appId>PC</appId>
                        <appVersion>3.2</appVersion>
                        <priceCheck>
                            <rateId>rate1</rateId>
                            <sender>
                                <country><![CDATA[""" + sender_country + """]]></country>
                                <town><![CDATA[""" + unidecode.unidecode(sender_town) + """]]></town>
                                <postcode>""" + str(sender_postcode) + """</postcode>
                            </sender>
                            <delivery>
                                <country><![CDATA[""" + delivery_country + """]]></country>
                                <town><![CDATA[""" + unidecode.unidecode(delivery_town) + """]]></town>
                                <postcode>""" + str(delivery_postcode) + """</postcode>
                            </delivery>
                            <collectionDateTime>""" + now.strftime('%Y-%m-%dT%H:%M:%S') + """</collectionDateTime>
                            <product>
                                <type>N</type>
                            </product>
                            <account>
                                <accountNumber>""" + str(account_number) + """</accountNumber>
                                <accountCountry>""" + str(account_country) + """</accountCountry>
                            </account>
                            <insurance>
                                <insuranceValue>""" + str(order.amount_total) + """</insuranceValue>
                                <goodsValue>""" + str(order.amount_total) + """</goodsValue>
                            </insurance>
                            <currency>EUR</currency>
                            <priceBreakDown>true</priceBreakDown>
                            <consignmentDetails>
                                <totalWeight>""" + str(package_weight) + """</totalWeight>
                                <totalVolume>0.001</totalVolume>
                                <totalNumberOfPieces>""" + str(package_pieces) + """</totalNumberOfPieces>
                            </consignmentDetails>
                        </priceCheck>
                    </priceRequest>
                    """
                    try:
                        response = requests.session().post(url, data=rate_request, headers=headers,timeout=5)
                    except (requests.exceptions.ConnectionError,requests.exceptions.Timeout) as e:
                        message_error += "TNT: Connection error on TNT webpage %s \n" % e
                        break
                    if response.status_code != 200:
                        message_error += "TNT: %s \n" % response.text
                        continue
                    if 'error' in response.url:
                        message_error += "TNT: Could not find information on url '%s' \n" % response.url
                        continue
                    response_data = response.text
                    try:
                        shipping_amount = 0.0
                        currency = ''
                        service_name = ''
                        transit_time = ''
                        root = ET.fromstring(response_data)
                        for price_response in root.iterfind('priceResponse'):
                            for rated_services in price_response.iterfind('ratedServices'):
                                currency_code = rated_services.find('currency')
                                if currency_code is not None:
                                    currency = currency_code.text
                                for children in rated_services.iter('ratedService'):
                                    amount_code = children.find('totalPriceExclVat')
                                    transit_code = children.find('estimatedTimeOfArrival')
                                    if amount_code is not None:
                                        shipping_amount = float(amount_code.text)
                                    if transit_code is not None:
                                        transit_time = transit_code.text.replace("T", " ")[:-3]
                                    product = children.find('product')
                                    if product is not None:
                                        product_description_code = product.find('id')
                                        if product_description_code is not None:
                                            service_code = product_description_code.text
                                    if shipping_amount and service_code:
                                        try:
                                            service_name = service_codes[service_code]
                                        except KeyError:
                                            message_error += "TNT: The service code \"%s\" is not defined in the system." % service_code
                                            continue
                                        rated_status = {
                                            'currency': currency,
                                            'transit_time': transit_time,
                                            'amount': shipping_amount,
                                            'service': service_name,
                                            'order_id': order.id,
                                            'wizard_id': new.id
                                        }
                                        new.write({'data': [(0, 0, rated_status)]})
                    except AttributeError:
                        message_error += "TNT: The response is not valid or it changed \n"
                        continue

                elif transporter.name == 'DHL':

                    dhl_services = order.env['transportation.transporter'].search([('name', '=', 'DHL')]).service_ids.mapped('name')
                    account_user = order.env['ir.config_parameter'].sudo().get_param('account.user.dhl.api.request')
                    account_password = order.env['ir.config_parameter'].sudo().get_param('account.password.dhl.api.request')
                    url = order.env['ir.config_parameter'].sudo().get_param('url.prod.dhl.api.request')
                    account_account = order.env['ir.config_parameter'].sudo().get_param('account.dhl.api.request')

                    shipper = order.env['res.company'].browse(1).partner_id
                    shipper_address_line = shipper.street
                    shipper_city = shipper.city
                    shipper_postal_code = shipper.zip
                    shipper_country_code = shipper.country_id.code

                    ship_to_address_line_1 = order.partner_shipping_id.street
                    ship_to_address_line_2 = order.partner_shipping_id.street2 if order.partner_shipping_id.street2 else ''
                    ship_to_city = order.partner_shipping_id.city
                    ship_to_postal_code = order.partner_shipping_id.zip
                    ship_to_country_code = order.partner_shipping_id.country_id.code
                    if order.partner_shipping_id.country_id in self.env['res.country.group'].browse([1]).country_ids:
                        content_doc = "DOCUMENTS"  # Just for Europe
                    else:
                        content_doc = "NON_DOCUMENTS"

                    auth = str(account_user) + ":" + str(account_password)
                    auth = auth.encode("utf-8")
                    byte_auth = bytearray(auth)
                    authentication = base64.b64encode(byte_auth).decode("utf-8")

                    timestamp = time.strftime("%Y-%m-%d") + 'T18:00:00GMT+02:00'

                    headers = {'content-type': 'application/json', 'Authorization': 'Basic %s' % str(authentication)}
                    rate_request = '''{
                        "RateRequest": {
                            "ClientDetails": "",
                            "RequestedShipment": {
                                "DropOffType": "REGULAR_PICKUP",
                                "ShipTimestamp": "%s",
                                "UnitOfMeasurement": "SI",
                                "Content": "%s",
                                "PaymentInfo": "DAP",
                                "Account": %s,
                                "NextBusinessDay": "N",
                                "Ship": {
                                    "Shipper": {
                                        "StreetLines": "%s",
                                        "StreetLines2": "N/A",
                                        "City": "%s",
                                        "PostalCode": "%s",
                                        "CountryCode": "%s"
                                    },
                                    "Recipient": {
                                        "StreetLines": "%s",
                                        "StreetLines2": "N/A",
                                        "City": "%s",
                                        "PostalCode": "%s",
                                        "CountryCode": "%s"
                                    }
                                },
                                "Packages": {
                                    "RequestedPackages": {
                                        "@number": "1",
                                        "Weight": {
                                            "Value": %s
                                        },
                                        "Dimensions": {
                                            "Length": 1.0,
                                            "Width": 1.0,
                                            "Height": 1.0
                                        }
                                    }
                                }
                            }
                        }
                    }''' % (timestamp, content_doc, int(account_account), shipper_address_line, shipper_city, shipper_postal_code,
                            shipper_country_code, (ship_to_address_line_1 + ship_to_address_line_2), ship_to_city,
                            ship_to_postal_code, ship_to_country_code, float(package_weight))
                    decoder = json.JSONDecoder(object_pairs_hook=collections.OrderedDict)
                    try:
                        response = requests.session().post(url, headers=headers,
                                                           data=json.dumps(decoder.decode(
                                                               rate_request.replace(" ", "").replace("\n", ""))),timeout=5)

                    except (requests.exceptions.ConnectionError,requests.exceptions.Timeout) as e:
                        message_error += "DHL: Connection error on DHL webpage. %s \n" % e
                        break
                    if response.status_code != 200:
                        message_error += "DHL: %s \n" % response.text
                        continue
                    if 'error' in response.url:
                        message_error += "DHL: Could not find information on url '%s' \n" % response.url
                        continue
                    info = json.loads(response.text)
                    if "RateResponse" in info:
                        if int(info["RateResponse"]["Provider"][0]["Notification"][0]["@code"]) !=0:
                            message_error+= "DHL: %s \n" % info["RateResponse"]["Provider"][0]["Notification"][0]["Message"]
                        else:
                            data = info["RateResponse"]["Provider"][0]["Service"]
                            if data and type(data) is list:
                                for service in data:
                                    dhl_services_dict = {i[-2:-1]: i for i in dhl_services}
                                    if service["@type"] in list(dhl_services_dict.keys()):
                                        transit_time = service["DeliveryTime"].replace("T", " ")[:-3]
                                        currency = service['TotalNet']['Currency']
                                        amount = service['Charges']['Charge'][0]['ChargeAmount'] + service['Charges']['Charge'][1]['ChargeAmount']
                                        rated_status = {
                                            'transit_time': transit_time,
                                            'currency': currency,
                                            'amount': amount,
                                            'service': 'DHL ' + dhl_services_dict[service["@type"]],
                                            'order_id': order.id,
                                            'wizard_id': new.id
                                        }
                                        new.write({'data': [(0, 0, rated_status)]})
                            elif data and type(data) is dict:
                                dhl_services_dict = {i[-2:-1]: i for i in dhl_services}
                                if data["@type"] in list(dhl_services_dict.keys()):
                                    currency = data['TotalNet']['Currency']
                                    amount = data['Charges']['Charge'][0]['ChargeAmount'] + data['Charges']['Charge'][1]['ChargeAmount']
                                    transit_time = data["DeliveryTime"].replace("T", " ")[:-3]
                                    rated_status = {
                                        'transit_time': transit_time,
                                        'currency': currency,
                                        'amount': amount,
                                        'service': 'DHL ' + dhl_services_dict[data["@type"]],
                                        'order_id': order.id,
                                        'wizard_id': new.id
                                    }
                                    new.write({'data': [(0, 0, rated_status)]})

        if message_error:
            new.message_error = message_error
        return {
            'name': 'Shipping Data Information',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'picking.rated.wizard',
            'src_model': 'stock.picking',
            'res_id': new.id,
            'type': 'ir.actions.act_window',
            'id': 'action_picking_rated_status',
            }


class TransportationTransporter(models.Model):
    _inherit = 'transportation.transporter'

    country_group_id = fields.Many2one('res.country.group', 'Country Group')


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    shipment = fields.Boolean('Shipment', default=False)
    transporter_ids = fields.One2many('transportation.transporter', 'country_group_id', readonly=True)
