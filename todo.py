# This file is part of todo module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import (
        Workflow, ModelView, ModelSQL,
        fields, sequence_ordered, tree)
from trytond.pyson import Eval, In, Equal, If, Bool, And
import datetime
from pytz import timezone

__all__ = ['Todo']

STATES = [
    ('open', 'Open'),
    ('done', 'Done'),
    ]

_STATES = {
    'readonly': Equal(Eval('state'), 'done'),
    }


class Todo(Workflow, ModelSQL, ModelView,
           sequence_ordered(), tree(separator='\\')):
    'Todo'
    __name__ = 'todo.todo'
    name = fields.Char('Name', required=True,
        states=_STATES, depends=['state'])
    date = fields.Function(fields.DateTime('Date'), 'get_date')
    limit_date = fields.DateTime('Limit Date',
        states=_STATES, depends=['state'])
    limit_state = fields.Function(
        fields.Integer('Limit state'),
        'get_limit_state')
    finish_date = fields.DateTime('Finish Date',
        states={
            'readonly': Equal(Eval('state'), 'done'),
            'invisible': Equal(Eval('state'), 'open')
            }, depends=['state'])
    user = fields.Function(fields.Many2One('res.user', 'User'), 'get_user')
    parent = fields.Many2One('todo.todo', 'Parent', select=True,
        states=_STATES, depends=['state'])
    childs = fields.One2Many('todo.todo', 'parent', string='Childs',
        states=_STATES, depends=['state'])
    description = fields.Text('Description',
        states=_STATES, depends=['state'])
    state = fields.Selection(STATES, 'State', readonly=True, required=True)

    @classmethod
    def __setup__(cls):
        super(Todo, cls).__setup__()
        cls._order = [
            ('sequence', 'ASC'),
            ('create_date', 'DESC'),
            ('id', 'DESC'),
            ]

        cls._transitions |= set(
            (
                ('open', 'done'),
                ('done', 'open'),
            ))

        cls._buttons.update({
            'done': {
                'invisible': In(Eval('state'), ['done']),
                },
            'open': {
                'invisible': In(Eval('state'), ['open']),
                },
            })

    @classmethod
    def view_attributes(cls):
        return [
            ('/tree/field[@name="name"]',
                'visual', If(Eval('limit_state', 0) > 0,
                            If(Eval('limit_state', 0) > 1,
                                'danger',
                                'warning'),
                            '')
            ),
            ]

    @staticmethod
    def default_state():
        return 'open'

    def get_limit_state(self, name):
        pool = Pool()
        Company = pool.get('company.company')
        timezone_str = None
        res = 0
        if self.limit_date:
            company_id = Transaction().context.get('company')
            if company_id:
                timezone_str = Company(company_id).timezone

            date = self.limit_date.astimezone(timezone(timezone_str))
            curr_date = datetime.datetime.now(timezone(timezone_str))

            date = date.date()
            curr_date = curr_date.date()
            if date == curr_date:
                res = 1  # Warning
            elif date < curr_date:
                res = 2  # Danger
        return res

    def get_date(self, name):
        return self.create_date.replace(microsecond=0)

    def get_user(self, name):
        return self.create_uid.id

    @classmethod
    def search_date(cls, name, clause):
        return [('create_date',) + tuple(clause[1:])]

    @classmethod
    @ModelView.button
    @Workflow.transition('open')
    def open(cls, todos):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def done(cls, todos):
        for todo in todos:
            todo.finish_date = datetime.datetime.now()
        cls.save(todos)
