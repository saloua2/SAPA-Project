from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    guarantee_percentage = fields.Float(compute='compute_guarantee_percentage')
    guarantee_return = fields.Boolean(string="Retenue de Garantie")
    rg_percentage = fields.Float('Pourcentage(RG)', default=5.0)
    date_echeance = fields.Date("Date d'échéance")
    prime_total_amount = fields.Float(compute='compute_prime_percentage')
    prime_amount = fields.Float("CEE Amount")
    prime = fields.Boolean(string="Prime CEE")

    @api.model
    def default_get(self, field_list=[]):
        rtn = super(SaleOrder, self).default_get(field_list)
        rtn['date_echeance'] = fields.Date.context_today(self).replace(fields.Date.context_today(self).year + 1)
        return rtn

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
        if self.guarantee_return:
            res.update({
                'guarantee_return': self.guarantee_return,
                'rg_percentage': self.rg_percentage,
            })
        return res

    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id', 'prime',
                 'prime_amount', 'rg_percentage', 'guarantee_return', 'guarantee_percentage')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            if order.prime:
                tax_totals['formatted_amount_total'] = tax_totals['formatted_amount_total'].replace(
                    str(tax_totals['amount_total']).replace('.', ','),
                    str(tax_totals['amount_total'] - order.prime_amount - order.guarantee_percentage).replace('.', ','))
                tax_totals['formatted_amount_untaxed'] = tax_totals['formatted_amount_untaxed'].replace(
                    str(tax_totals['amount_untaxed']).replace('.', ','),
                    str(tax_totals['amount_untaxed'] - order.prime_amount - order.guarantee_percentage).replace('.',
                                                                                                                ','))
                tax_totals['amount_total'] -= order.prime_amount
                tax_totals['amount_untaxed'] -= order.prime_amount
                tax_totals['prime_amount'] = order.prime_amount
                tax_totals['prime_amount_formatted'] = '{:.2f}'.format(
                    order.prime_amount - order.guarantee_percentage).replace('.',
                                                                             ',') + ' ' + str(
                    order.currency_id.symbol)
            if order.guarantee_return:
                tax_totals['formatted_amount_total'] = tax_totals['formatted_amount_total'].replace(
                    str(tax_totals['amount_total']).replace('.', ','),
                    str(tax_totals['amount_total'] - order.guarantee_percentage).replace('.', ','))
                tax_totals['formatted_amount_untaxed'] = tax_totals['formatted_amount_untaxed'].replace(
                    str(tax_totals['amount_untaxed']).replace('.', ','),
                    str(tax_totals['amount_untaxed'] - order.guarantee_percentage).replace('.',
                                                                                           ','))
                tax_totals['amount_total'] -= order.guarantee_percentage
                tax_totals['amount_untaxed'] -= order.guarantee_percentage

                tax_totals['guarantee_percentage'] = order.guarantee_percentage
                tax_totals['guarantee_percentage_formatted'] = '{:.2f}'.format(order.guarantee_percentage).replace(
                    '.',
                    ',') + str(order.currency_id.symbol)
            order.tax_totals = tax_totals
