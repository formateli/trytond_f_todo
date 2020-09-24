# This file is part of todo module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import (
        Workflow, ModelView, ModelSQL,
        fields, sequence_ordered, tree)
from trytond.pyson import Eval, In, Equal, If, Bool, And
from trytond.i18n import gettext
from trytond.exceptions import UserWarning
import datetime
from pytz import timezone


class Todo(Workflow, ModelSQL, ModelView,
           sequence_ordered(), tree(separator=' / ')):
    'TODO task'
    __name__ = 'todo.todo'

    _states = {
        'readonly': Equal(Eval('state'), 'done'),
        }
    _depends = ['state']

    name = fields.Char('Name', required=True,
        states=_states, depends=_depends)
    date = fields.Function(fields.DateTime('Date'), 'get_date')
    limit_date = fields.DateTime('Limit Date',
        states=_states, depends=_depends)
    limit_state = fields.Function(
        fields.Integer('Limit state'),
        'get_limit_state')
    finish_date = fields.DateTime('Finish Date',
        states={
            'readonly': Equal(Eval('state'), 'done'),
            'invisible': Equal(Eval('state'), 'open')
            }, depends=_depends)
    user = fields.Function(fields.Many2One('res.user', 'User'), 'get_user')
    parent = fields.Many2One('todo.todo', 'Parent', select=True,
        domain=[
            ('create_uid', '=', Eval('create_uid'))
        ],
        states=_states, depends=_depends + ['create_uid'])
    childs = fields.One2Many('todo.todo', 'parent', string='Childs',
        states=_states, depends=_depends)
    childs_open = fields.One2Many('todo.todo', 'parent', string='Childs Open',
        states=_states, depends=_depends, filter=[('state', '=', 'open')])
    description = fields.Text('Description',
        states=_states, depends=_depends)
    state = fields.Selection([
        ('open', 'Open'),
        ('done', 'Done'),
        ], 'State', readonly=True, required=True)

    del _states, _depends

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
            ('/tree/field[@name="name"]', 'visual',
                If(And(Eval('limit_state', 0) > 0,
                       Eval('state', '') == 'open'),
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
        finish_date = datetime.datetime.now()
        to_done = cls._set_done(todos, finish_date, False)
        cls.save(to_done)

    @classmethod
    def _set_done(cls, todos, finish_date, done_childs):
        pool = Pool()
        Warning = pool.get('res.user.warning')
        to_done = []
        for todo in todos:
            todo.state = 'done'
            todo.finish_date = finish_date
            to_done.append(todo)
            if todo.childs:
                if not done_childs:
                    msg_id = 'todo_done_childs_' + str(todo.id)
                    if Warning.check(msg_id):
                        raise UserWarning(
                            msg_id,
                            gettext(
                                'todo.msg_todo_done_childs',
                                todo=todo.rec_name)
                            )
                to_done += cls._set_done(todo.childs, finish_date, True)
        return to_done
