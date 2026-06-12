import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import markupsafe


class IdeaRequest(models.Model):
    _name = 'idea.request'
    _description = 'Idea / Feature Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'score desc, create_date desc'

    # Basic fields
    name = fields.Char(string='Title', required=True, tracking=True)
    number = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    description = fields.Html(string='Description', sanitize=True)
    state = fields.Selection([
        ('new', 'New'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('declined', 'Declined'),
        ('duplicate', 'Duplicate'),
    ], string='Status', default='new', required=True, tracking=True, group_expand='_group_expand_state')

    # Relations
    submitter_id = fields.Many2one('res.users', string='Submitted By', default=lambda self: self.env.user, readonly=True)
    tag_ids = fields.Many2many('idea.tag', string='Tags')
    duplicate_of_id = fields.Many2one('idea.request', string='Duplicate Of', domain="[('id', '!=', id)]")
    converted_task_id = fields.Many2one('project.task', string='Converted Task', readonly=True)
    vote_ids = fields.One2many('idea.vote', 'idea_id', string='Votes')

    # Voting
    upvote_count = fields.Integer(string='Upvotes', compute='_compute_vote_counts', store=True)
    downvote_count = fields.Integer(string='Downvotes', compute='_compute_vote_counts', store=True)
    score = fields.Integer(string='Score', compute='_compute_vote_counts', store=True)
    user_vote = fields.Selection([
        ('up', 'Upvote'),
        ('down', 'Downvote'),
        ('none', 'None'),
    ], string='My Vote', compute='_compute_user_vote')

    # Trending
    vote_count = fields.Integer(string='Total Votes', compute='_compute_vote_counts', store=True)
    comment_count = fields.Integer(string='Comments', compute='_compute_comment_count', store=True)
    trending_score = fields.Float(string='Trending Score', compute='_compute_trending_score')
    days_since_creation = fields.Float(string='Age (Days)', compute='_compute_age')

    # Response / admin note
    response = fields.Html(string='Official Response', sanitize=True)
    response_user_id = fields.Many2one('res.users', string='Responded By', readonly=True)
    response_date = fields.Datetime(string='Responded On', readonly=True)

    # Computed text for kanban snippets
    description_text = fields.Text(string='Description Text', compute='_compute_description_text', store=True)

    # Voters (for avatars)
    voter_ids = fields.Many2many('res.users', string='Upvoters', compute='_compute_voters')
    downvoter_ids = fields.Many2many('res.users', string='Downvoters', compute='_compute_voters')

    # ------------------------------------------------------------------
    # Defaults / Sequences
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', 'New') == 'New':
                vals['number'] = self.env['ir.sequence'].next_by_code('idea.request') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('description')
    def _compute_description_text(self):
        for idea in self:
            if idea.description:
                text = re.sub(r'<[^>]+>', ' ', idea.description)
                text = re.sub(r'\s+', ' ', text).strip()
                idea.description_text = text[:280]
            else:
                idea.description_text = ''
    @api.depends('vote_ids', 'vote_ids.vote_type')
    def _compute_vote_counts(self):
        idea_ids = self.ids
        if not idea_ids:
            for idea in self:
                idea.upvote_count = 0
                idea.downvote_count = 0
                idea.score = 0
                idea.vote_count = 0
            return
        domain = [('idea_id', 'in', idea_ids)]
        groups = self.env['idea.vote'].read_group(
            domain,
            ['idea_id', 'vote_type'],
            ['idea_id', 'vote_type'],
            lazy=False,
        )
        data = {}
        for group in groups:
            idea_id = group['idea_id'][0]
            vote_type = group['vote_type']
            count = group['__count']
            data.setdefault(idea_id, {})[vote_type] = count
        for idea in self:
            upvotes = data.get(idea.id, {}).get('up', 0)
            downvotes = data.get(idea.id, {}).get('down', 0)
            idea.upvote_count = upvotes
            idea.downvote_count = downvotes
            idea.score = upvotes - downvotes
            idea.vote_count = upvotes + downvotes

    @api.depends('message_ids')
    def _compute_comment_count(self):
        for idea in self:
            idea.comment_count = len(idea.message_ids.filtered(lambda m: m.message_type == 'comment' and not m.is_internal))

    @api.depends('create_date')
    def _compute_age(self):
        now = fields.Datetime.now()
        for idea in self:
            if idea.create_date:
                idea.days_since_creation = (now - idea.create_date).total_seconds() / 86400.0
            else:
                idea.days_since_creation = 0.0

    @api.depends('score', 'vote_count', 'comment_count', 'days_since_creation')
    def _compute_trending_score(self):
        """Simple trending: score weighted by recency and engagement.

        Formula inspired by Reddit/Hacker News hot ranking:
        trending = (score + comment_weight) / (age_hours + 2)^gravity
        """
        for idea in self:
            engagement = idea.score + (idea.comment_count * 0.5) + (idea.vote_count * 0.2)
            age_hours = max(idea.days_since_creation * 24, 0.5)
            gravity = 1.8
            idea.trending_score = engagement / (age_hours ** gravity)

    @api.depends('vote_ids', 'vote_ids.vote_type', 'vote_ids.user_id')
    def _compute_user_vote(self):
        self.env['idea.vote'].flush_model(['idea_id', 'user_id', 'vote_type'])
        idea_ids = self.ids
        if not idea_ids:
            for idea in self:
                idea.user_vote = 'none'
            return
        votes = self.env['idea.vote'].search_read(
            [('idea_id', 'in', idea_ids), ('user_id', '=', self.env.uid)],
            ['idea_id', 'vote_type'],
        )
        vote_map = {v['idea_id'][0]: v['vote_type'] for v in votes}
        for idea in self:
            idea.user_vote = vote_map.get(idea.id, 'none')

    @api.depends('vote_ids', 'vote_ids.vote_type', 'vote_ids.user_id')
    def _compute_voters(self):
        for idea in self:
            up_votes = idea.vote_ids.filtered(lambda v: v.vote_type == 'up')
            down_votes = idea.vote_ids.filtered(lambda v: v.vote_type == 'down')
            idea.voter_ids = up_votes.mapped('user_id')
            idea.downvoter_ids = down_votes.mapped('user_id')

    # ------------------------------------------------------------------
    # Group expand for kanban columns
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_state(self, states, domain):
        return [key for key, val in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_upvote(self):
        self.ensure_one()
        vote = self.env['idea.vote'].search([
            ('idea_id', '=', self.id),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if vote:
            vote.unlink()
            self.message_post(
                body=markupsafe.Markup('<b>%s</b> removed their vote.') % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        else:
            self.env['idea.vote'].create({'idea_id': self.id, 'vote_type': 'up'})
            self.message_post(
                body=markupsafe.Markup('<b>%s</b> upvoted this idea.') % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        self.message_subscribe(partner_ids=[self.env.user.partner_id.id])

    def action_downvote(self):
        self.ensure_one()
        vote = self.env['idea.vote'].search([
            ('idea_id', '=', self.id),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if vote:
            vote.unlink()
            self.message_post(
                body=markupsafe.Markup('<b>%s</b> removed their vote.') % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        else:
            self.env['idea.vote'].create({'idea_id': self.id, 'vote_type': 'down'})
            self.message_post(
                body=markupsafe.Markup('<b>%s</b> downvoted this idea.') % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        self.message_subscribe(partner_ids=[self.env.user.partner_id.id])

    def action_clear_vote(self):
        self.ensure_one()
        vote = self.env['idea.vote'].search([
            ('idea_id', '=', self.id),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if vote:
            vote.unlink()

    def action_open_converted_task(self):
        self.ensure_one()
        if not self.converted_task_id:
            raise UserError(_('No converted task linked to this idea.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': self.converted_task_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_plan(self):
        self.write({'state': 'planned'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'done'})

    def action_decline(self):
        self.write({'state': 'declined'})

    def action_reopen(self):
        self.write({'state': 'new'})

    def action_clear_duplicate(self):
        self.ensure_one()
        if self.state != 'duplicate':
            raise UserError(_('Only duplicate ideas can be cleared.'))
        self.write({
            'state': 'new',
            'duplicate_of_id': False,
        })
        self.message_post(
            body=markupsafe.Markup('<b>%s</b> cleared the duplicate status.') % self.env.user.name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    @api.onchange('duplicate_of_id')
    def _onchange_duplicate_of_id(self):
        if not self.duplicate_of_id and self._origin.state == 'duplicate':
            self.state = 'new'
