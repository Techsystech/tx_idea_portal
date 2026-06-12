from odoo import api, fields, models, _
from odoo.exceptions import UserError
import markupsafe


class IdeaMarkDuplicateWizard(models.TransientModel):
    _name = 'idea.mark.duplicate.wizard'
    _description = 'Mark Idea as Duplicate'

    idea_id = fields.Many2one('idea.request', string='Idea', required=True,
                              default=lambda self: self.env.context.get('active_id'))
    original_idea_id = fields.Many2one('idea.request', string='Original Idea', required=True,
                                       domain="[('id', '!=', idea_id), ('state', '!=', 'duplicate')]")

    def action_mark_duplicate(self):
        self.ensure_one()
        idea = self.idea_id
        if idea.state == 'duplicate':
            raise UserError(_('This idea is already marked as a duplicate.'))
        if idea.id == self.original_idea_id.id:
            raise UserError(_('An idea cannot be a duplicate of itself.'))

        idea.write({
            'state': 'duplicate',
            'duplicate_of_id': self.original_idea_id.id,
        })
        idea.message_post(
            body=markupsafe.Markup(
                'Marked as duplicate of <a href="#" data-oe-model="idea.request" data-oe-id="%s">%s</a>.'
            ) % (self.original_idea_id.id, self.original_idea_id.name),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        self.original_idea_id.message_post(
            body=markupsafe.Markup(
                '<a href="#" data-oe-model="idea.request" data-oe-id="%s">%s</a> was marked as a duplicate of this idea.'
            ) % (idea.id, idea.name),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}
