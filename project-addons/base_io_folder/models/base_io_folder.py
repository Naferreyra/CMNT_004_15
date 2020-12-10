# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from base64 import b64encode, b64decode


def source_name(directory, file_name):
    """helper to get the full name"""
    return directory + os.sep + file_name


class BaseIOFolder(models.Model):
    _name = "base.io.folder"

    name = fields.Char(required=True)
    directory_path = fields.Char(
        required=True,
        help="Directory path from where you want to import or export files")
    company_id = fields.Many2one(comodel_name='res.company', required=True,
                                 string='Company')
    after_import = fields.Selection(
        selection=[('backup', 'Backup File'), ('delete', 'Delete File')],
        default='backup', required=True,
        help="After the import, you can either delete the file either move "
             "it to a backup directory")
    backup_path = fields.Char(
        help="Directory where you want to move the file after the import")
    direction = fields.Selection([('import', 'Import files'),
                                  ('export', 'Export files')], required=True,
                                 default="import")

    @api.model
    def _scheduler_import_file(self, max_commit_length=False):
        """
            Launch the scanning for all configurations defined
        :return:
        """
        for config in self.search([('direction', '=', 'import')]):
            continue_search = True
            while continue_search:
                imported_files, continue_search = config._iter_directory(max_commit_length)
                self.env.cr.commit()
                for file_imported, file_full_name in imported_files:
                    config._after_import(file_imported, file_full_name)

    @api.multi
    def _get_files_in_directory(self, max_commit_length=False):
        """
            Load a list of all file names existing in the directory
        :return: list of file names
        """
        self.ensure_one()
        list = os.listdir(self.directory_path)
        continue_search = max_commit_length and len(list) > max_commit_length
        if continue_search:
            list = list[:max_commit_length]
        return list, continue_search

    @api.multi
    def _after_import(self, file_name, file_path):
        """
            Manage the after import process of a file. It can be
            either deleted or moved to a backup directory depending on the
            configuration
        :param file_name: the name of the file to manage
        :param file_path: the full path of the file to manage
        :return:
        """
        self.ensure_one()
        if self.after_import == 'backup':
            if not os.path.exists(self.backup_path):
                raise ValidationError(_('Unknown backup path provided: %s'
                                        % self.backup_path))
            backup_full_name = source_name(self.backup_path,
                                           file_name)
            os.rename(file_path, backup_full_name)
        elif self.after_import == 'delete':
            os.remove(file_path)

    @api.multi
    def _iter_directory(self, max_commit_length=False):
        """
            Scan the directory linked to the current configuration and launch
            a queue job for each file found. Each job will call the invoice
            import wizard.
        :return: None
        """
        self.ensure_one()
        imported_files = []
        if not os.path.exists(self.directory_path):
            raise ValidationError(_('Unknown path provided: %s'
                                    % self.directory_path))
        files, continue_search = self._get_files_in_directory(max_commit_length)

        for file_imported in files:
            file_full_name = source_name(self.directory_path,
                                         file_imported)
            with open(file_full_name, "rb") as fileobj:
                data = fileobj.read()
            self.action_batch_import(file_imported, b64encode(data))
            imported_files.append((file_imported, file_full_name))
        return imported_files, continue_search

    @api.multi
    def export_file(self, b64data, filename):
        self.ensure_one()
        if not os.path.exists(self.directory_path):
            raise ValidationError(_('Unknown path provided: %s'
                                    % self.directory_path))
        file_full_name = source_name(self.directory_path, filename)
        with open(file_full_name, 'wb') as fileobj:
            fileobj.write(b64decode(b64data))

    def action_batch_import(self, file_name, file_content):
        """
            Method to manage the call to the import wizard for each
            file found in the configuration directory
        :param file_name: Name of the file to load
        :param file_content: Content of the file to load
        :return: Result of invoice import wizard
        """
        pass
