'''

    whooshalchemy flask extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adds whoosh indexing capabilities to SQLAlchemy models for Flask applications
    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''

from flaskext.sqlalchemy import models_committed

import sqlalchemy

from whoosh.qparser import MultifieldParser
from whoosh import index
from whoosh.analysis import StemmingAnalyzer
import whoosh
from whoosh.fields import Schema, TEXT, KEYWORD, ID, STORED

import os


class Searcher(object):
    def __init__(self, model, indx):
        self.model = model
        self.primary = _get_attributes(model, False, True)
        self.searcher = indx.searcher()
        self.index = indx
        fields = set(indx.schema._fields.keys()) - set([self.primary])
        self.parser = MultifieldParser(list(fields), indx.schema)

    def __call__(self, query, limit=None):
        results = [x[self.primary] for x in
                self.index.searcher().search(self.parser.parse(query), limit=limit)]

        return self.model.__class__.query.filter(getattr(self.model.__class__,
            self.primary).in_(results))


def whoosh_index(app, model):
    if not hasattr(app, 'whoosh_indexes'):
        app.whoosh_indexes = {}

    indx = app.whoosh_indexes.get(model.__class__.__name__)
    if indx is None:
        if not app.config.get('WHOOSH_INDEX'):
            app.config['WHOOSH_INDEX'] = './whoosh_index2'

        wi = os.path.join(app.config.get('WHOOSH_INDEX'), model.__class__.__name__)

        if whoosh.index.exists_in(wi):
            indx = whoosh.index.open_dir(wi)
        else:
            if not os.path.exists(wi):
                os.makedirs(wi)
            indx = whoosh.index.create_in(wi, _get_attributes(model, True))

        app.whoosh_indexes[model.__class__.__name__] = indx
        model.__class__.search_query = Searcher(model, indx)
    return indx


def _get_attributes(model, as_schema, get_primary=False):
    # http://stackoverflow.com/questions/9398664/how-can-i-dynamically-get-a-list-of-primary-key-attributes-from-an-sqlalchemy-cl
    import inspect
    predicate = lambda x: isinstance(x, sqlalchemy.orm.attributes.InstrumentedAttribute)
    fields = inspect.getmembers(model.__class__, predicate=predicate)
    values = {}
    for x, y in fields:
        if hasattr(y.property, 'columns'):
            if y.property.columns[0].primary_key:
                if get_primary:
                    return x
                if as_schema:
                    values[x] = whoosh.fields.ID(stored=True, unique=True)
                else:
                    values[x] = unicode(getattr(model, x))
            elif x in model.__class__.__searchable__:
                if type(y.property.columns[0].type) == sqlalchemy.types.Text:
                    if as_schema:
                        values[x] = whoosh.fields.TEXT(analyzer=StemmingAnalyzer())
                    else:
                        values[x] = getattr(model, x)

    if as_schema:
        return Schema(**values)
    return values


def after_flush(app, changes):
    bytype = {}
    for change in changes:
        update = change[1] in ('update', 'insert')

        if hasattr(change[0].__class__, '__searchable__'):
            bytype.setdefault(change[0].__class__.__name__, []).append((update, change[0]))

    for typ, values in bytype.iteritems():
        index = whoosh_index(app, values[0][1])
        with index.writer() as writer:
            primary_field = _get_attributes(values[0][1], False, True)
            for update, v in values:
                writer.delete_by_term(primary_field, unicode(getattr(v, primary_field)))

                if update:
                    attrs = _get_attributes(v, False)
                    writer.add_document(**attrs)


models_committed.connect(after_flush)
