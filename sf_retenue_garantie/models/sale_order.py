from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    guarantee_percentage = fields.Float(compute='compute_guarantee_percentage')
    guarantee_return = fields.Boolean(string="Retenue de Garantie")
    prime = fields.Boolean(string="Prime CEE")

    @api.depends('amount_total')
    def compute_guarantee_percentage(self):
        self.guarantee_percentage = self.amount_total * 0.05
