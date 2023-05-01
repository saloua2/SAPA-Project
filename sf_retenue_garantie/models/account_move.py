from odoo import api, fields, models, _
from odoo.tools import formatLang
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    guarantee_percentage = fields.Float(compute='compute_guarantee_percentage')
    sale_order_id = fields.Many2one('sale.order')
    guarantee_return = fields.Boolean(string="Retenue de Garantie")
    rg_percentage = fields.Float('Pourcentage(RG)')
    date_echeance = fields.Date("Date d'échéance", compute='compute_date_echeance', readonly=False)
    prime_total_amount = fields.Float(compute='compute_prime_percentage')
    prime_amount = fields.Float("CEE Amount")
    prime = fields.Boolean(string="Prime CEE")
    invoice_line_ids = fields.One2many(  # /!\ invoice_line_ids is just a subset of line_ids.
        'account.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        readonly=True,
        domain= lambda self: self.env['account.move.line']._domain_invoice_line_ids(),
        states={'draft': [('readonly', False)]},
    )

    @api.depends('amount_total', 'prime_amount')
    def compute_prime_percentage(self):
        for rec in self:
            rec.prime_total_amount = rec.amount_total - rec.prime_amount

    @api.depends('amount_total')
    def compute_guarantee_percentage(self):
        for rec in self:
            rec.guarantee_percentage = rec.amount_total * (rec.rg_percentage / 100)

    def compute_date_echeance(self):
        for rec in self:
            rec.date_echeance = fields.Date.context_today(self).replace(fields.Date.context_today(self).year + 1)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        account_id = self.env['account.account'].search([('code', '=', '467300')])
        product_id = self.env['product.product'].search([('property_account_income_id','=',account_id.id)])
        currency_id = account_id.company_id.currency_id
        if 'invoice_vendor_bill_id' in fields_list:
            res['invoice_line_ids'] = [[0, 0, {'product_id': product_id.id, 'name':'RG', 'account_id': account_id.id,
                                             'quantity': 1.0, 'price_unit': 0.0, 'tax_ids': False,
                                             'price_subtotal': 0.0, 'currency_id': currency_id.id}]]
        return res

    @api.onchange('prime_amount', 'prime')
    def onchange_price_unit(self):
        for rec in self:
            account_id = self.env['account.account'].search([('code', '=', '467300')])
            line_id = rec.invoice_line_ids.filtered(lambda line: line.account_id.id == account_id.id)
            if rec.prime:
                if line_id:
                    line_id.price_unit = -rec.prime_amount
            if not rec.prime:
                # rec.write({'invoice_line_ids': [(3, line_id.id, False)], 'prime_amount': 0.0})
                rec.write({'prime_amount': 0.0})
                if line_id:
                    line_id.price_unit = 0.0

    # def _domain_invoice_line_ids(self):
    #     domain = {}
    #     for rec in self:
    #         if rec.invoice_date:
    #             account_id = self.env['account.account'].search([('code', '=', '467300')])
    #
    #             if account_id:
    #                 domain = {'domain': {'invoice_line_ids': [('account_id', '!=', account_id.id)]}}
    #             return domain

    def action_post(self):
        due_date = fields.Date.context_today(self).replace(fields.Date.context_today(self).year + 1)
        res = super(AccountMove, self).action_post()
        vals = {
            'name': _('New'),
            'invoice_number': self.name,
            'customer_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'amount': self.guarantee_percentage,
            'due_date': due_date
        }
        self.env['sf.retenue.guarantee'].create(vals)
        if self.prime:
            account = self.env['account.account'].search([('code', '=', '467300000')], limit=1)
            vals_cee = {
                'name': _('New'),
                'invoice_number': self.name,
                'origin_move_id': self.id,
                'invoice_date': self.invoice_date,
                'customer_id': self.partner_id.id,
                'amount': self.prime_total_amount,
                'due_date': self.invoice_date_due,
                'account_id': account.id
            }
            self.env['sf.prime.cee'].create(vals_cee)
        return res

    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'guarantee_percentage',
        'rg_percentage',
        'guarantee_return',
        'prime_amount',
        'prime')
    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]

                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    sign = -1 if move.is_inbound(include_receipts=True) else 1
                    base_line_values_list += [
                        {
                            **line._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id or move.journal_id.currency_id or move.company_id.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                        ))
                move.tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)
                rounding_line = move.line_ids.filtered(lambda l: l.display_type == 'rounding')
                if rounding_line:
                    amount_total_rounded = move.tax_totals['amount_total'] - rounding_line.balance
                    move.tax_totals['formatted_amount_total_rounded'] = formatLang(self.env, amount_total_rounded,
                                                                                   currency_obj=move.currency_id) or ''

                if move.prime and move.guarantee_return:
                    move.tax_totals['custom'] = '{:.2f}'.format(
                        move.tax_totals['amount_total'] - (move.prime_amount + move.guarantee_percentage)).replace('.',
                                                                                                                   ',') + ' ' + str(
                        move.currency_id.symbol)
                    move.tax_totals['amount_total'] -= move.prime_amount
                    move.tax_totals['prime_amount'] = move.prime_amount
                    move.tax_totals['prime_amount_formatted'] = '{:.2f}'.format(move.prime_amount).replace('.',
                                                                                                           ',') + ' ' + str(
                        move.currency_id.symbol)
                    move.tax_totals['guarantee_percentage'] = move.guarantee_percentage
                    move.tax_totals['guarantee_percentage_formatted'] = '{:.2f}'.format(
                        move.guarantee_percentage).replace('.',
                                                           ',') + ' ' + str(move.currency_id.symbol)
                elif move.prime:
                    move.tax_totals['formatted_amount_total'] = move.tax_totals['formatted_amount_total'].replace(
                        str(move.tax_totals['amount_total']).replace('.', ','),
                        str(move.tax_totals['amount_total'] - move.prime_amount).replace(
                            '.', ','))
                    move.tax_totals['custom'] = move.tax_totals['formatted_amount_total'].replace(
                        '{:.2f}'.format(move.tax_totals['amount_total']).replace('.', ','),
                        '{:.2f}'.format(move.tax_totals['amount_total'] - move.prime_amount).replace(
                            '.', ','))
                    # move.tax_totals['custom'] = move.tax_totals['formatted_amount_total'].replace(
                    #     str(move.tax_totals['amount_total']).replace('.', ','),
                    #     str(move.tax_totals['amount_total'] - move.prime_amount).replace(
                    #         '.', ','))

                    move.tax_totals['formatted_amount_untaxed'] = move.tax_totals['formatted_amount_untaxed'].replace(
                        str(move.tax_totals['amount_untaxed']).replace('.', ','),
                        str(move.tax_totals['amount_untaxed'] - move.prime_amount).replace(
                            '.', ','))
                    move.tax_totals['amount_total'] -= move.prime_amount
                    move.tax_totals['prime_amount'] = move.prime_amount
                    move.tax_totals['prime_amount_formatted'] = '{:.2f}'.format(move.prime_amount).replace('.',
                                                                                                           ',') + ' ' + str(
                        move.currency_id.symbol)
                elif move.guarantee_return:
                    move.tax_totals['formatted_amount_total'] = move.tax_totals['formatted_amount_total'].replace(
                        str(move.tax_totals['amount_total']).replace('.', ','),
                        str(move.tax_totals['amount_total'] - move.prime_amount).replace(
                            '.', ','))
                    move.tax_totals['custom'] = move.tax_totals['formatted_amount_total'].replace(
                        str(move.tax_totals['amount_total']).replace('.', ','),
                        str(move.tax_totals['amount_total']).replace(
                            '.', ','))
                    # move.tax_totals['formatted_amount_untaxed'] = move.tax_totals['formatted_amount_untaxed'].replace(
                    #     str(move.tax_totals['amount_untaxed']).replace('.', ','),
                    #     str(move.tax_totals['amount_untaxed'] - move.guarantee_percentage).replace(
                    #         '.', ','))
                    # move.tax_totals['amount_total'] -= move.guarantee_percentage

                    # move.tax_totals['amount_untaxed'] -= move.guarantee_percentage

                    move.tax_totals['guarantee_percentage'] = move.guarantee_percentage
                    move.tax_totals['guarantee_percentage_formatted'] = '{:.2f}'.format(
                        move.guarantee_percentage).replace('.',
                                                           ',') + str(move.currency_id.symbol)
                else:
                    move.tax_totals['custom'] = move.tax_totals['formatted_amount_total']

            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state',
        'prime_amount',
        'prime',
        'rg_percentage',
        'guarantee_return',
        'guarantee_percentage')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            if move.prime:

                move.amount_residual -= move.prime_amount
                move.amount_total -= move.prime_amount
            if move.guarantee_return:
                move.amount_residual -= move.guarantee_percentage
                move.amount_total -= move.guarantee_percentage

    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.balance',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id',
    #     'state',
    #     'prime_amount',
    #     'prime',
    #     'rg_percentage',
    #     'guarantee_return',
    #     'guarantee_percentage'
    #     )
    # def _compute_amount(self):
    #     for move in self:
    #         total_untaxed, total_untaxed_currency = 0.0, 0.0
    #         total_tax, total_tax_currency = 0.0, 0.0
    #         total_residual, total_residual_currency = 0.0, 0.0
    #         total, total_currency = 0.0, 0.0
    #
    #         for line in move.line_ids:
    #             if move.is_invoice(True):
    #                 # === Invoices ===
    #                 if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
    #                     # Tax amount.
    #                     total_tax += line.balance
    #                     total_tax_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.display_type in ('product', 'rounding'):
    #                     # Untaxed amount.
    #                     total_untaxed += line.balance
    #                     total_untaxed_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.display_type == 'payment_term':
    #                     # Residual amount.
    #                     total_residual += line.amount_residual
    #                     total_residual_currency += line.amount_residual_currency
    #             else:
    #                 # === Miscellaneous journal entry ===
    #                 if line.debit:
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #
    #         sign = move.direction_sign
    #         move.amount_untaxed = sign * total_untaxed_currency
    #         move.amount_tax = sign * total_tax_currency
    #         move.amount_total = sign * total_currency
    #         move.amount_residual = -sign * total_residual_currency
    #         move.amount_untaxed_signed = -total_untaxed
    #         move.amount_tax_signed = -total_tax
    #         move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
    #         move.amount_residual_signed = total_residual
    #         move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(
    #                     sign * move.amount_total)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('balance', 'move_id.is_storno')
    def _compute_debit_credit(self):
        for line in self:
            if not line.is_storno:
                line.debit = line.balance if line.balance > 0.0 else 0.0
                line.credit = -line.balance if line.balance < 0.0 else 0.0
            else:
                line.debit = line.balance if line.balance < 0.0 else 0.0
                line.credit = -line.balance if line.balance > 0.0 else 0.0

    @api.model
    def _domain_invoice_line_ids(self):
        res = [('account_id', '=', 0)]  # Nothing accepted by domain, by default
        account_id = self.env['account.account'].search([('code', '=', '467300')])

        if account_id:
            res = [('account_id', '!=', account_id.id), ('display_type', 'in', ('product', 'line_section', 'line_note'))]
        return res