from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        res = super().write(vals)
        if vals.get('payment_state') in ('paid', 'in_payment'):
            for move in self:
                if move.move_type == 'out_invoice':
                    move._generate_commission_lines_from_payment()
        return res

    def _generate_commission_lines_from_payment(self):
        self.ensure_one()
        Commission = self.env['sale.commission.line']
        if Commission.search_count([('invoice_id', '=', self.id)]):
            return  # already generated for this invoice

        for line in self.invoice_line_ids:
            sale_lines = line.sale_line_ids
            if not sale_lines or not line.product_id:
                continue
            order = sale_lines[0].order_id
            plan = order.commission_plan_id
            if not plan or plan.basis != 'invoice_payment':
                continue

            rate = plan._get_rate_for_product(line.product_id)
            if plan.calc_method == 'margin':
                cost = line.product_id.standard_price * line.quantity
                base = line.price_subtotal - cost
            else:
                base = line.price_subtotal

            Commission.create({
                'salesperson_id': order.user_id.id,
                'sale_order_id': order.id,
                'sale_order_line_id': sale_lines[0].id,
                'invoice_id': self.id,
                'product_id': line.product_id.id,
                'plan_id': plan.id,
                'base_amount': base,
                'rate': rate,
                'commission_amount': base * (rate / 100.0),
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
            })
