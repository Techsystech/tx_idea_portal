from odoo import api, fields, models


class IdeaVote(models.Model):
    _name = 'idea.vote'
    _description = 'Idea Vote'
    _sql_constraints = [
        ('user_idea_uniq', 'UNIQUE(user_id, idea_id)', 'User can only vote once per idea.'),
    ]

    user_id = fields.Many2one('res.users', string='User', required=True, index=True, default=lambda self: self.env.user)
    idea_id = fields.Many2one('idea.request', string='Idea', required=True, index=True, ondelete='cascade')
    vote_type = fields.Selection([
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    ], string='Vote Type', required=True)
    create_date = fields.Datetime(string='Voted On', readonly=True)
