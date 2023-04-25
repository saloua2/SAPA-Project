from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    return_prime = fields.Boolean(string="Retenue de Garantie et Prime CEE", default=False)
