from odoo import api, fields, models, _
from odoo.exceptions import UserError
import markupsafe


class IdeaConvertTaskWizard(models.TransientModel):
    _name = 'idea.convert.task.wizard'
    _description = 'Convert Idea to Task'

    idea_id = fields.Many2one('idea.request', string='Idea', required=True,
                              default=lambda self: self.env.context.get('active_id'))
    project_id = fields.Many2one('project.project', string='Project', required=True)

    def action_convert(self):
        self.ensure_one()
        idea = self.idea_id
        if idea.converted_task_id:
            raise UserError(_('This idea has already been converted to a task.'))

        task = self.env['project.task'].create({
            'name': idea.name,
            'description': idea.description,
            'project_id': self.project_id.id,
            'user_ids': [(6, 0, [self.env.uid])],
        })
        idea.converted_task_id = task.id
        idea.state = 'done'
        idea.response = markupsafe.Markup(
            '<p>Idea converted to task <a href="#" data-oe-model="project.task" data-oe-id="%s">%s</a>.</p>'
        ) % (task.id, task.name)
        idea.response_user_id = self.env.uid
        idea.response_date = fields.Datetime.now()

        task.message_post(
            body=markupsafe.Markup(
                'Created from idea <a href="#" data-oe-model="idea.request" data-oe-id="%s">%s</a>.'
            ) % (idea.id, idea.name)
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
