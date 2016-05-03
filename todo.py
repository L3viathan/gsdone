#!/usr/local/bin/python3
"""Simple TodoTracker

Usage:
    todo.py
    todo.py add <name> [--parent=<pid>]
    todo.py set <id> <field> <value>
    todo.py require <id> <other>
    todo.py move <id> <pid>
    todo.py done <id>
    todo.py delete <id>
    todo.py show
    todo.py (-h | --help)
    todo.py --version

Options:
    --parent=<pid>  Parent to attach to [default: HEAD].
    --version       Show version.
    -h --help       Show this screen.

"""
import json
import os.path
from uuid import uuid4
from docopt import docopt

class ChildrenNotCompleted(Exception):
    pass

class OrphanError(Exception):
    pass

class ItemNotFound(Exception):
    pass

class UnknownField(Exception):
    pass

def load_storage():
    try:
        with open(os.path.expanduser("~/.todo-data")) as f:
            storage = json.load(f)
    except FileNotFoundError:
        storage = {
                "HEAD": {
                        'id': "HEAD",
                        'children': [],
                        'parent': None,
                        'requires': [],  # keep permanently empty
                        'status': 'closed',
                        'format': 0,
                        }
                  }
    return storage

def save_storage(storage):
    with open(os.path.expanduser("~/.todo-data"), "w") as f:
        json.dump(storage, f)

def expand_id(storage, id):
    if id in storage:
        return id
    starting_with = [candidate_id for candidate_id in storage if candidate_id.startswith(id)]
    if len(starting_with) == 1:  # exactly one match
        return starting_with[0]
    raise ItemNotFound(id)

def todo_add(storage, name, pid):
    if pid is None:
        pid = "HEAD"
    uuid = uuid4().hex
    pid = expand_id(storage, pid)
    storage[pid]['children'].append(uuid)
    storage[uuid] = {
                   'name': name,
                   'id': uuid,
                   'parent': pid,
                   'children': [],
                   'requires': [],
                   'status': 'open',
                  }
    return uuid

def todo_show(storage, pid, level=0):
    for child in storage[pid]['children']:
        if storage[child]['status'] != 'closed':
            print("  "*level, "[{:.8s}] -- {}".format(child, storage[child]['name']), sep='')
            todo_show(storage, child, level+1)

def todo_set(storage, id, field, value):
    if field not in ('deadline', 'comment',):
        raise UnknownField(field)
    id = expand_id(storage, id)
    storage[id][field] = value

def todo_require(storage, id, other_id):
    dependent = expand_id(storage, id)
    dependency = expand_id(storage, other_id)  # just to make sure it exists
    if dependency not in storage[dependent]['requires']:
        storage[dependent]['requires'].append(dependency)
    print("Added dependency: [{:.8s}] requires [{:.8s}] to be done.".format(dependent, dependency))

def todo_move(storage, id, pid):
    pid = expand_id(storage, pid)
    id = expand_id(storage, id)
    storage[storage[id]['parent']]['children'].remove(id)
    storage[pid]['children'].append(id)
    storage[id]['parent'] = pid

def todo_done(storage, id):
    id = expand_id(storage, id)
    if any(storage[cid]['status'] != 'closed' for cid in storage[id]['children']):
        raise ChildrenNotCompleted  # maybe later allow this and mark all children done?
    storage[id]['status'] = 'closed'
    print("Marked as done: [{:.8s}] -- {}".format(id, storage[id]['name']))

def todo_delete(storage, id):
    id = expand_id(storage, id)
    if storage[id]['children']:
        raise OrphanError
    storage[storage[id]['parent']]['children'].remove(id)
    print("Deleted [{:.8s}] -- {}".format(id, storage[id]['name']))
    del storage[id]

def todo(storage):
    for node in storage:
        if all(storage[dep]['status'] == 'closed' for dep in storage[node]['requires']):
            if storage[node]['status'] == 'open':
                print("[{:.8s}] -- {}".format(node, storage[node]['name']))


if __name__ == '__main__':
    args = docopt(__doc__, version="0.1.0")
    storage = load_storage()
    if args['add']:
        id = todo_add(storage, args['<name>'], args['--parent'])
        print("Added [{:.8s}] -- {}".format(id, storage[id]['name']))
    elif args['show']:
        todo_show(storage, 'HEAD')
    elif args['set']:
        todo_set(storage, args['<id>'], args['<field>'], args['<value>'])
    elif args['require']:
        todo_require(storage, args['<id>'], args['<other>'])
    elif args['move']:
        todo_move(storage, args['<id>'], args['<pid>'])
    elif args['done']:
        todo_done(storage, args['<id>'])
    elif args['delete']:
        todo_delete(storage, args['<id>'])
    else:  # no arguments
        todo(storage)
    save_storage(storage)
