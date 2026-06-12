{
    'name': 'Idea Portal',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Internal feature request and idea portal with voting, comments, and task conversion',
    'description': """
Idea Portal
===========

An internal feature request system inspired by Fider.

Features:
- Submit ideas and feature requests with descriptions
- Upvote / downvote ideas
- Comment on ideas via the chatter
- Categorize ideas with tags and colors
- Track ideas through states: New → Planned → In Progress → Done / Declined / Duplicate
- Filter and view trending ideas
- Convert any idea into a Project task in one click
- Kanban, list, and form views with analytics

Designed for internal teams to collect and prioritize feedback.
    """,
    'author': 'Techsystech',
    'website': 'https://techsystech.io',
    'depends': ['base', 'mail', 'project'],
    'data': [
        'security/idea_security.xml',
        'security/ir.model.access.csv',
        'data/idea_data.xml',
        'views/idea_tag_views.xml',
        'views/idea_request_views.xml',
        'views/idea_convert_task_wizard_views.xml',
        'views/idea_mark_duplicate_wizard_views.xml',
        'views/idea_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'tx_idea_portal/static/src/scss/idea_portal.scss',
        ],
    },
}
