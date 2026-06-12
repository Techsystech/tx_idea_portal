from odoo import api, fields, models


class IdeaTag(models.Model):
    _name = 'idea.tag'
    _description = 'Idea Tag'
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Tag name must be unique.'),
    ]

    name = fields.Char(string='Name', required=True, index=True)
    color = fields.Integer(string='Color Index')
    is_public = fields.Boolean(string='Public', default=True)
    idea_count = fields.Integer(string='Ideas', compute='_compute_idea_count')

    @api.depends('name')
    def _compute_idea_count(self):
        for tag in self:
            tag.idea_count = self.env['idea.request'].search_count([('tag_ids', 'in', tag.id)])
