from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    guarantee_percentage = fields.Float(compute='compute_guarantee_percentage')
    guarantee_return = fields.Boolean(string="Retenue de Garantie")
    rg_percentage = fields.Float('Pourcentage(RG)', default=5.0)
    prime_total_amount = fields.Float(compute='compute_prime_percentage')
    prime_amount = fields.Float("CEE Amount")
    prime = fields.Boolean(string="Prime CEE")

    @api.depends('amount_total')
    def compute_guarantee_percentage(self):
        self.guarantee_percentage = self.amount_total * (self.rg_percentage / 100)

    @api.depends('amount_total', 'prime_amount')
    def compute_prime_percentage(self):
        for rec in self:
            rec.prime_total_amount = rec.amount_total - rec.prime_amount

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.prime:
            res.update({
                'prime': self.prime,
                'prime_amount': self.prime_amount,
            })
        return res
