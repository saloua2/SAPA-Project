# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    advance_payment_method = fields.Selection(selection_add=[
        ('retenue_de_garantie', 'Retenue de garantie')],
        ondelete={'retenue_de_garantie': 'cascade'})
    guarantee_percentage = fields.Float(string="Pourcentage(RG)")
    due_date = fields.Date("Date d'échéance")
    prime_amount = fields.Float("CEE Amount")
    prime = fields.Boolean(string="Prime CEE")

    @api.model
    def default_get(self, fields):
        res = super(SaleAdvancePaymentInv, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            sale_order = self.env['sale.order'].browse(active_id)
            date_order = sale_order.date_order
            res.update({
                'prime_amount': sale_order.prime_amount or 0.0,
                'prime': sale_order.prime,
                'guarantee_percentage': sale_order.rg_percentage,
                'due_date': date_order.replace(date_order.year + 1)
            })
        return res

    # def create_invoices(self):
    #     print("advance_payment_method******",self.advance_payment_method)
    #     res = super(SaleAdvancePaymentInv, self).create_invoices()
    #     if self.advance_payment_method not in ['delivered','percentage','fixed']:
    #         print('guarantee_percentage**********', self.guarantee_percentage)
    #     else:
    #         res = super(SaleAdvancePaymentInv,self).create_invoices()
    #         return res

    def _create_invoices(self, sale_orders):
        """ Override method from sale/wizard/sale_make_invoice_advance.py

            When the user want to invoice the timesheets to the SO
            up to a specific period then we need to recompute the
            qty_to_invoice for each product_id in sale.order.line,
            before creating the invoice.
        """

        if self.advance_payment_method == 'retenue_de_garantie':
            if self.guarantee_percentage:
                invoices = sale_orders.with_context(active_test=False)._create_invoices(final=self.deduct_down_payments)
                for invoice in invoices:
                    invoice.prime = self.prime
                    if self.prime:
                        invoice.prime_amount = self.prime_amount
                return invoices

        invoices = sale_orders.with_context(active_test=False)._create_invoices(final=self.deduct_down_payments)
        account_id = self.env['account.account'].search([('code', '=', '467300')])
        product_id = self.env['product.product'].search([('property_account_income_id', '=', account_id.id)])
        currency_id = account_id.company_id.currency_id
        for invoice in invoices:
            invoice.prime = self.prime
            if self.prime:
                invoice.prime_amount = self.prime_amount
                price_unit = -1 * self.prime_amount
                invoice.invoice_line_ids = [[0, 0, {'product_id': product_id.id, 'name':'RG', 'account_id': account_id.id,
                                             'quantity': 1.0, 'price_unit': price_unit, 'tax_ids': False,
                                             'price_subtotal': 0.0, 'currency_id': currency_id.id}]]

        return invoices