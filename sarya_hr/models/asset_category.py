from odoo import fields, models


class AssetHistory(models.Model):
    _name = 'asset.category'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    asset_category_id = fields.Many2one('asset.category', string="Parent Category")
    is_vehicle = fields.Boolean('Is Vehicle')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', default=lambda self: self.env.company)

    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         if rec.asset_category_id:
    #             result.append((rec.id, '%s / %s' % (rec.asset_category_id.name, rec.name)))
    #     return result
