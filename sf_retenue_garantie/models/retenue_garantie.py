from odoo import api, fields, models


class RetenueGarantie(models.Model):
    _name = 'sf.retenue.guarantee'
    _description = 'Retenue de garantie'
    _order = 'id desc'

    name = fields.Char('Retenue de ganatie')
    invoice_number = fields.Char('Numéro de la facture')
    customer_id = fields.Many2one('res.partner', 'Client')
    amount = fields.Float('Montant')
    due_date = fields.Date("Date d'échance")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        copy=False,
        tracking=True,
        default='draft',
    )
    active = fields.Boolean(string="Active", default=True)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def reset_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})