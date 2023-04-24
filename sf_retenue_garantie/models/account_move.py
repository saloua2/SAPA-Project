from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    guarantee_percentage = fields.Float(compute='compute_guarantee_percentage')
    sale_order_id = fields.Many2one('sale.order')
    guarantee_return = fields.Boolean(string="Retenue de Garantie")
    rg_percentage = fields.Float('Pourcentage(RG)')
    prime_total_amount = fields.Float(compute='compute_prime_percentage')
    prime_amount = fields.Float("CEE Amount")
    prime = fields.Boolean(string="Prime CEE")

    @api.depends('amount_total', 'prime_amount')
    def compute_prime_percentage(self):
        for rec in self:
            rec.prime_total_amount = rec.amount_total - rec.prime_amount

    @api.depends('amount_total')
    def compute_guarantee_percentage(self):
        self.guarantee_percentage = self.amount_total * 0.05

    def action_post(self):
        due_date = fields.Date.context_today(self).replace(fields.Date.context_today(self).year + 1)
        res = super(AccountMove, self).action_post()
        vals = {
            'name': 'Draft',
            'invoice_number': self.name,
            'customer_id': self.partner_id.id,
            'amount': self.guarantee_percentage,
            'due_date': due_date
        }
        self.env['sf.retenue.guarantee'].create(vals)
        if self.prime:
            vals_cee = {
                'name': 'Draft',
                'invoice_number': self.name,
                'customer_id': self.partner_id.id,
                'amount': self.prime_total_amount,
                'due_date': fields.Date.context_today(self)
            }
            self.env['sf.retenue.guarantee'].create(vals_cee)
            # if self.move_type == 'out_invoice':
            #     account = self.env['account.account'].search([('code', '=', '467300')], limit=1)
            #     vals_credit = {
            #         'name': _('Automatic Balancing CEE'),
            #         'move_id': self.id,
            #         'account_id': account.id,
            #         'debit': 0,
            #         'credit': self.prime_amount}
            #     self.env['account.move.line'].create(vals_credit)

        res = super(AccountMove, self).action_post()
        return res



