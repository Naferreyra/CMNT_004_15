from odoo import http,_
from odoo.addons.web.controllers.main import content_disposition
from io import BytesIO
import zipfile
from odoo.http import request

class View(http.Controller):

    @http.route('/web/binary/downloadAll/model=<string:model>/id=<int:id>', type='http', auth="user")
    def download_all(self,id,model):
        attachments = request.env['ir.attachment'].search([('res_id','=',id),('res_model','=',model)])
        file_dict = {}
        for attach in attachments:
            file_store = attach.store_fname
            if file_store:
                file_name = attach.name
                file_path = attach._full_path(file_store)
                file_dict["%s:%s" % (file_store, file_name)] = dict(path=file_path, name=file_name)
        object_id = request.env[model].browse(id)
        zip_filename = _("%s-Attachments.zip") % object_id.name
        bit_io = BytesIO()
        zip_file = zipfile.ZipFile(bit_io, "w", zipfile.ZIP_DEFLATED)
        for file_info in file_dict.values():
            zip_file.write(file_info["path"], file_info["name"])
        zip_file.close()
        return request.make_response(bit_io.getvalue(),
                                     headers=[('Content-Type', 'application/x-zip-compressed'),
                                              ('Content-Disposition', content_disposition(zip_filename))])