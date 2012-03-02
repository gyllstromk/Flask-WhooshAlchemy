'''

    whooshalchemy flask extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adds whoosh indexing capabilities to SQLAlchemy models for Flask applications
    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''

from __future__ import absolute_import


from flaskext.sqlalchemy import models_committed

import sqlalchemy

from whoosh.qparser import MultifieldParser
from whoosh import index
from whoosh.analysis import StemmingAnalyzer
import whoosh
from whoosh.fields import Schema, TEXT, KEYWORD, ID, STORED

import os


class Searcher(object):
    ''' Assigned to a Model class as ``search_query``, which enables
    text-querying. '''

    def __init__(self, model, primary, indx):
        self.model = model
        self.primary = primary
        self.index = indx
        self.searcher = indx.searcher()
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
        if not app.config.get('WHOOSH_BASE'):
            app.config['WHOOSH_BASE'] = './whoosh_index'

        wi = os.path.join(app.config.get('WHOOSH_BASE'), model.__class__.__name__)

        schema, primary =_get_schema_and_primary(model)

        if whoosh.index.exists_in(wi):
            indx = whoosh.index.open_dir(wi)
        else:
            if not os.path.exists(wi):
                os.makedirs(wi)
            indx = whoosh.index.create_in(wi, schema)

        app.whoosh_indexes[model.__class__.__name__] = indx
        model.__class__.search_query = Searcher(model, primary, indx)
    return indx


def _get_schema_and_primary(model):
    import inspect
    predicate = lambda x: isinstance(x, sqlalchemy.orm.attributes.InstrumentedAttribute)
    fields = inspect.getmembers(model.__class__, predicate=predicate)
    schema = {}
    primary = None
    for x, y in fields:
        if hasattr(y.property, 'columns'):
            if y.property.columns[0].primary_key:
                schema[x] = whoosh.fields.ID(stored=True, unique=True)
                primary = x
            elif x in model.__class__.__searchable__:
                if type(y.property.columns[0].type) == sqlalchemy.types.Text:
                    schema[x] = whoosh.fields.TEXT(analyzer=StemmingAnalyzer())

    return Schema(**schema), primary


def after_flush(app, changes):
    ''' Any db updates go through here. We check if any of these models have
    ``__searchable__`` fields, indicating they need to be indexed. With these
    we update the whoosh index for the model. If no index exists, it will be
    created here; this could impose a penalty on the initial commit of a model.
    '''

    bytype = {}  # sort changes by type so we can use per-model writer
    for change in changes:
        update = change[1] in ('update', 'insert')

        if hasattr(change[0].__class__, '__searchable__'):
            bytype.setdefault(change[0].__class__.__name__, []).append((update, change[0]))

    for typ, values in bytype.iteritems():
        index = whoosh_index(app, values[0][1])
        with index.writer() as writer:
            primary_field = values[0][1].search_query.primary
            searchable = values[0][1].__searchable__

            for update, v in values:
                writer.delete_by_term(primary_field, unicode(getattr(v, primary_field)))

                if update:
                    attrs = dict((key, getattr(v, key)) for key in searchable)
                    attrs[primary_field] = unicode(getattr(v, primary_field))
                    writer.add_document(**attrs)


models_committed.connect(after_flush)
