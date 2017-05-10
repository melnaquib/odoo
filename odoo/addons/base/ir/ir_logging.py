# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class IrLogging(models.Model):
    _name = 'ir.logging'
    _order = 'id DESC'

    create_date = fields.Datetime(readonly=True)
    # Integer not m2o is intentionnal
    create_uid = fields.Integer(string='Uid', readonly=True)
    name = fields.Char(required=True)
    type = fields.Selection(
        [('client', 'Client'), ('server', 'Server')], required=True, index=True)
    dbname = fields.Char(string='Database Name', index=True)
    level = fields.Char(index=True)
    message = fields.Text(required=True)
    path = fields.Char(required=True)
    func = fields.Char(string='Function', required=True)
    line = fields.Char(required=True)
