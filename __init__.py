# This file is part of todo module.
# The COPYRIGHT file at the top level of this repository
# contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import todo


def register():
    Pool.register(
        todo.Todo,
        module='todo', type_='model')
