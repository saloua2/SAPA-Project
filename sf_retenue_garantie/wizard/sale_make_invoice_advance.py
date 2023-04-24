# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    advance_payment_method = fields.Selection(selection_add=[
        ('retenue_de_garantie', 'Retenue de garantie')],
        ondelete={'retenue_de_garantie': 'cascade'})
    guarantee_percentage = fields.Float(string="Pourcentage", default=5.0)

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
                return sale_orders.with_context()._create_invoices(final=self.deduct_down_payments)

        return super()._create_invoices(sale_orders)



