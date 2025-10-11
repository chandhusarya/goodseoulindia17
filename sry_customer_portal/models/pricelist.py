from odoo import fields, models, api


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    def compute_price_rule_get_package_items(self, prod_tmpl_ids, pricelist_id, packaging_id):
        self.env.cr.execute(
            """
            SELECT
                item.id
            FROM
                product_pricelist_item AS item
            WHERE
                (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                AND (item.pricelist_id = %s)
                AND (item.packging_id = %s)
                AND (item.date_start<=%s)
                AND (item.date_end>=%s)
            """,
            (prod_tmpl_ids, pricelist_id, packaging_id, fields.Date.today(), fields.Date.today()))

        item_ids = [x[0] for x in self.env.cr.fetchall()]
        print("item_ids", item_ids)
        if len(item_ids) > 0:
            return self.env['product.pricelist.item'].browse(item_ids)
        else:
            self.env.cr.execute(
                """
                SELECT
                    item.id
                FROM
                    product_pricelist_item AS item
                WHERE
                    (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                    AND (item.pricelist_id = %s)
                    AND (item.packging_id = %s)
                    AND (item.date_start IS NULL)
                    AND (item.date_end IS NULL)
                """,
                (prod_tmpl_ids, pricelist_id, packaging_id))

            item_ids = [x[0] for x in self.env.cr.fetchall()]
            return self.env['product.pricelist.item'].browse(item_ids)
