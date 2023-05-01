# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    advance_payment_method = fields.Selection(selection_add=[
        ('retenue_de_garantie', 'Retenue de garantie'), ('prime_cee', 'Prime CEE')],
        ondelete={
            'retenue_de_garantie': 'cascade',
            'prime_cee': 'cascade',
        },
    )
    guarantee_percentage = fields.Float(string="Pourcentage(RG)")
    amount_total = fields.Float(string="Amount Total")
    due_date = fields.Date("Date d'échéance")
    prime_amount = fields.Float("CEE Amount")
    prime = fields.Boolean(string="Prime CEE")
    guarantee_return = fields.Boolean(string="Retenue de garantie")

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
                'amount_total': sale_order.amount_total,
                'guarantee_return': sale_order.guarantee_return,
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

        invoices = sale_orders.with_context(active_test=False)._create_invoices(final=self.deduct_down_payments)

        if self.advance_payment_method == 'retenue_de_garantie':
            if self.guarantee_percentage:

                for invoice in invoices:
                    invoice.rg_percentage = self.guarantee_percentage
                # return invoices

        if self.advance_payment_method == 'prime_cee':
            for invoice in invoices:
                invoice.prime = self.prime
                if self.prime:
                    invoice.prime_amount = self.prime_amount
                    invoice.guarantee_return = True
            # return invoices
        account_id = self.env['account.account'].search([('code', '=', '467300000')])
        rg_account_id = self.env['account.account'].search([('code', '=', '411700000')])
        product_id = self.env['product.product'].search([('property_account_income_id', '=', account_id.id)])
        rg_product_id = self.env['product.product'].search([('property_account_income_id', '=', rg_account_id.id)])
        currency_id = account_id.company_id.currency_id
        for invoice in invoices:
            invoice.prime = self.prime
            for invoice in invoices:
                invoice.prime = self.prime
                invoice_line_ids = []
                # if self.prime:
                invoice.prime_amount = self.prime_amount
                if self.prime:
                    price_unit = -1 * self.prime_amount
                else:
                    price_unit = 0
                invoice_line_ids.append((0, 0,
                                         {'product_id': product_id.id, 'name': 'Prime CEE', 'account_id': account_id.id,
                                          'quantity': 1.0, 'price_unit': price_unit, 'tax_ids': False,
                                          'price_subtotal': 0.0, 'currency_id': currency_id.id}))
                if self.guarantee_return:
                    rg_price_unit = -1 * self.amount_total * (self.guarantee_percentage / 100)
                else:
                    rg_price_unit = 0
                invoice_line_ids.append((0, 0, {'product_id': rg_product_id.id, 'name': 'RG',
                                                'account_id': rg_account_id.id,
                                                'quantity': 1.0, 'price_unit': rg_price_unit, 'tax_ids': False,
                                                'price_subtotal': 0.0, 'currency_id': currency_id.id}))
            if invoice_line_ids:
                invoice.invoice_line_ids = invoice_line_ids

        return invoices
