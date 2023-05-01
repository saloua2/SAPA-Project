from odoo import api, fields, models, _


class RetenueGarantie(models.Model):
    _name = 'sf.retenue.guarantee'
    _description = 'Retenue de garantie'
    _order = 'id desc'

    name = fields.Char('Retenue de ganatie', copy=False, default=lambda self: _('New'))
    invoice_number = fields.Char('Numéro de la facture')
    customer_id = fields.Many2one('res.partner', 'Client')
    amount = fields.Float('Montant')
    due_date = fields.Date("Date d'échance (RG)")
    invoice_date = fields.Date("Date de la facture")
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
    invoice_date = fields.Date("Date de la facture")
    active = fields.Boolean(string="Active", default=True)

    def action_confirm(self):
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('seq.retenue.guarantee') or _('New')
        self.write({'state': 'confirmed'})

    def reset_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
