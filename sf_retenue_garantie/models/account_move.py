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
        self.guarantee_percentage = self.amount_total * (self.rg_percentage/100)

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

        # res = super(AccountMove, self).action_post()
        return res

    def action_entry(self):
        compte_rg = self.env['account.account'].search([('code', '=', '411700')], limit=1)
        print('****compte_rg***', compte_rg)
        for rec in self:
            move = {
                'name': "/",
                'date': self.invoice_date,
                'journal_id': self.journal_id.id,
                'company_id': self.company_id.id,
                'partner_id': self.partner_id.id,
                'move_type': 'entry',
                'state': 'draft',
                'ref': self.name + '- ' + 'RG',
                'line_ids': [(0, 0, {
                    'name': _("Test"),
                    'partner_id': self.partner_id.id,
                    'account_id': compte_rg.id,
                    'debit': self.guarantee_percentage}),
                             (0, 0, {
                                 'name': "/",
                                 'partner_id': self.partner_id.id,
                                 'account_id': compte_rg.id,
                                 'credit': self.guarantee_percentage
                             })]
            }
            line_ids = []
            move_id = self.env['account.move'].create(move)

            line_ids += [(0, 0, move_id.id)]
            move.update({'line_ids': line_ids})
            print("move_id ************", move_id)




