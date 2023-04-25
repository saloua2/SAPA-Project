from odoo import api, fields, models


class PrimeCEE(models.Model):
    _name = 'sf.prime.cee'
    _description = 'Retenue de garantie'

    name = fields.Char('Prime CEE')
    invoice_number = fields.Char('Numéro de la facture')
    customer_id = fields.Many2one('res.partner', 'Client')
    amount = fields.Float('Montant')
    due_date = fields.Date("Date d'échance")
    move_id = fields.Many2one('account.move', 'Invoice')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancel', 'Cancelled'),
            ('invoiced', 'Facturé'),
        ],
        string='Status',
        copy=False,
        tracking=True,
        default='draft',
    )
    account_id = fields.Many2one(
        comodel_name='account.account',string="Account"
    )
    active = fields.Boolean(string="Active", default=True)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def reset_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def create_invoice(self):
        product_prime_energie = self.env.ref('sf_retenue_garantie.product_prime_energie')
        product_prime_cee = self.env.ref('sf_retenue_garantie.product_prime_cee')

        selected_records = self.env['sf.prime.cee'].browse(self.env.context.get('active_ids'))
        records_by_customer = {}
        if not selected_records:
            if self.id:
                selected_records = self
        for record in selected_records:
            if record.customer_id in records_by_customer:
                records_by_customer[record.customer_id].append(record)
            else:
                records_by_customer[record.customer_id] = [record]
        invoices = []
        for customer, records in records_by_customer.items():
            invoice_lines = []
            for record in records:
                if not record.state == 'invoiced':
                    invoice_lines.append((0, 0, {
                        'product_id': product_prime_energie.id,
                        'name': product_prime_energie.description,
                        'price_unit': 17.5,
                        'account_id': record.account_id.id,
                        'tax_ids': [],
                    }))
                    invoice_lines.append((0, 0, {
                        'product_id': product_prime_cee.id,
                        'name': product_prime_cee.description,
                        'price_unit': record.amount,
                        'account_id': record.account_id.id,
                        'tax_ids': [],
                    }))

            if invoice_lines:
                invoice = self.env['account.move'].create({
                    'partner_id': customer.id,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': invoice_lines,
                })
                invoices.append(invoice)
                for record in records:
                    record.move_id = invoice.id
                    record.state = 'invoiced'
        # Return the action to open the invoices
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices[0].id
        else:
            action['domain'] = [('id', 'in', [invoice.id for invoice in invoices])]
        return action
