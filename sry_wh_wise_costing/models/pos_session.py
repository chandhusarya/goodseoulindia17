from odoo import models, api

class POSSession(models.Model):
    _inherit = 'pos.session'

    def update_journal_item_values(self):
        for session in self:
            pickings = session.picking_ids | session._get_closed_orders().mapped('picking_ids')
            stock_account_moves = pickings.mapped('move_ids.account_move_ids')
            other_related_moves = session._get_other_related_moves()

            debit, credit = 0, 0

            # -----------------------------
            # Calculate COGS difference
            # -----------------------------
            for line in stock_account_moves.line_ids:
                if line.account_id.id == 828:  # Stock Out Account
                    debit += line.debit
                    credit += line.credit

            balance = debit - credit
            # print("COGS Balance:", balance)

            # ============================================
            # 1. UPDATE COGS VALUE IN SALES ENTRY
            # ============================================
            if self.move_id :
                cogs_line = self.move_id.line_ids.filtered(lambda l: l.account_id.id == 822)  # Replace 500 with COGS account ID
                stock_out_line = self.move_id.line_ids.filtered(lambda l: l.account_id.id == 828)  # Replace 500 with COGS account ID
                if cogs_line and stock_out_line:
                    # print("cogs_line", cogs_line, "stock_out_line", stock_out_line)
                    # Update debit or credit depending on sign
                    if balance > 0:
                        self.move_id.write({
                            'line_ids': [
                                (1, cogs_line.id, {'debit': balance, 'credit': 0}),
                                (1, stock_out_line.id, {'debit': 0, 'credit': balance}),
                            ]
                        })

                        # cogs_line.debit = balance
                        # cogs_line.credit = 0
                        # stock_out_line.credit = balance
                        # stock_out_line.debit = 0
                    # else:
                    #     cogs_line.credit = abs(balance)
                    #     cogs_line.debit = 0
                    #     stock_out_line.credit = abs(balance)
                    #     stock_out_line.debit = 0

            # ============================================
            # 2. RECONCILE STOCK OUT ENTRIES
            # ============================================
            # Stock out lines from stock moves
            stock_out_lines = stock_account_moves.line_ids.filtered(
                lambda l: l.account_id.id == 828
            )

            # Stock out lines inside invoice (usually credit)
            inv_stock_out_lines = self.move_id.line_ids.filtered(
                lambda l: l.account_id.id == 828
            )
            # Only reconcile matching debit/credit
            lines_to_reconcile = stock_out_lines | inv_stock_out_lines

            if len(lines_to_reconcile) > 1:
                try:
                    lines_to_reconcile.reconcile()
                    print("Stock Out Account reconciled")
                except Exception as e:
                    print("Reconciliation failed:", e)
