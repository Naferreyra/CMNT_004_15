#!/usr/bin/env python3

import sys
import json
import random
import urllib.request

from datetime import datetime
from dateutil.relativedelta import MO, SU, relativedelta
import xlwt


class weekly_stock_report(object):
    def __init__(self, dbname, user, passwd, start_date, end_date,
                 name_file_dest):
        """método incial"""

        try:
            self.url_template = "http://%s:%s/jsonrpc"
            self.server = "localhost"
            self.port = 8069
            self.dbname = dbname
            self.user_name = user
            self.user_passwd = passwd
            self.start_date = start_date
            self.end_date = end_date
            self.name_file_dest = name_file_dest
            if '.xls' not in name_file_dest:
                raise Exception('El nombre del fichero destino tiene que '
                                'terminar en .xls')

            #
            # Conectamos con Odoo
            #
            self.user_id = self.call("common", "login", self.dbname,
                                     self.user_name, self.user_passwd)

            res = self.create_stock_report()
            # con exito
            if res:
                print("All created")
        except Exception as e:
            print("ERROR: {}".format(e))
            sys.exit(1)

    def json_rpc(self, url, method, params):
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": random.randint(0, 1000000000),
        }
        req = urllib.request.\
            Request(url=url, data=json.dumps(data).encode(),
                    headers={"Content-Type": "application/json"})
        reply = json.loads(urllib.request.urlopen(req).read().decode('UTF-8'))
        if reply.get("error"):
            raise Exception(reply["error"])
        return reply["result"]

    def call(self, service, method, *args):
        return self.json_rpc(self.url_template % (self.server, self.port),
                             "call", {"service": service, "method": method,
                                      "args": args})

    def search(self, model, query, offset=0, limit=False, order=False,
               count=False):
        """
        Wrapper del metodo search.
        """
        ids = self.call("object", "execute", self.dbname, self.user_id,
                        self.user_passwd, model, 'search',
                        query, offset, limit, order, count)
        return ids

    def read_group(self, model, domain, fields, groupby, offset=0, limit=False,
                   orderby=False, lazy=False):
        """
        Wrapper del metodo read_group.
        """
        res = self.call("object", "execute", self.dbname, self.user_id,
                        self.user_passwd, model, 'read_group', domain, fields,
                        groupby, offset, limit, orderby, lazy)
        return res

    def read(self, model, ids, fields):
        data = self.call("object", "execute", self.dbname, self.user_id,
                         self.user_passwd, model, 'read', ids, fields)
        return data

    def create_stock_report(self):
        start_date = datetime.strptime(self.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(self.end_date, "%Y-%m-%d").date()
        next_sunday = start_date+relativedelta(weekday=SU)
        days = abs(start_date - end_date).days
        weeks = (days//7)
        if not weeks:
            weeks = 1
        wb = xlwt.Workbook()
        week = 0
        while (next_sunday <= end_date):
            week += 1
            ws = wb.add_sheet(start_date.strftime("%d%m%Y") + " - " +
                              next_sunday.strftime("%d%m%Y"))
            print("NEW SHEET: {}".format(start_date.strftime("%d/%m/%Y") +
                                         " - " +
                                         next_sunday.strftime("%d/%m/%Y")))
            line = 0
            ws.write(line, 0, "Producto")
            ws.write(line, 1, "Uds.")
            ws.write(line, 2, "Zona")
            ws.write(line, 3, "Fecha entrada")

            product_stock_data = self.\
                read_group("stock.history",
                           [('product_id.type', '=', 'product'),
                            ('location_id.usage', '=', 'internal'),
                            ('date', '<=',
                             next_sunday.strftime("%Y-%m-%d 23:23:59"))],
                           ['product_id', 'location_id', 'quantity'],
                           ['product_id', 'location_id'])
            for data in product_stock_data:
                if data['quantity']:
                    line += 1
                    move_ids = self.\
                        search("stock.move",
                               [('product_id', '=', data['product_id'][0]),
                                ('location_dest_id', '=',
                                 data['location_id'][0]),
                                ('date', '<=',
                                 next_sunday.strftime("%Y-%m-%d")),
                                ('state', '=', 'done')],
                               limit=1, order="date desc")
                    in_date = move_ids and \
                        self.read('stock.move', move_ids,
                                  ['date'])[0]['date'][:11] or ""
                    ws.write(line, 0, data['product_id'][1])
                    ws.write(line, 1, data['quantity'])
                    ws.write(line, 2, data['location_id'][1])
                    ws.write(line, 3, in_date)
            print("Week {} de {}".format(week, weeks))

            start_date = next_sunday+relativedelta(weekday=MO)
            next_sunday = start_date+relativedelta(weekday=SU)
        wb.save(self.name_file_dest)

        return True


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("""Uso: {} <dbname> <user> <password> <date_start (AAAA-MM-DD)>
 <date_end (AAAA-MM-DD)> <name_file_dest.xls>""".format(sys.argv[0]))
    else:
        weekly_stock_report(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
                            sys.argv[5], sys.argv[6])
