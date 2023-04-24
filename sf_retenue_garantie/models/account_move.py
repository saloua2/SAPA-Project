from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    guarantee_percentage = fields.Float(compute='compute_guarantee_percentage')

    @api.depends('amount_total')
    def compute_guarantee_percentage(self):
        self.guarantee_percentage = self.amount_total * 0.05

    def action_post(self):
        res = super(AccountMove, self).action_post()
        vals = {
            'name': 'Draft',
            'invoice_number': self.name,
            'customer_id': self.partner_id.id,
            'amount': self.amount_total,
            'due_date': fields.Date.context_today(self)
        }
        self.env['sf.retenue.guarantee'].create(vals)
        return res



