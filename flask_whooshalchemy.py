'''

    whooshalchemy flask extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adds whoosh indexing capabilities to SQLAlchemy models for Flask
    applications.

    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''

from __future__ import absolute_import


from flask_sqlalchemy import models_committed

import sqlalchemy

from whoosh.qparser import MultifieldParser
from whoosh.analysis import StemmingAnalyzer
import whoosh.index
from whoosh.fields import Schema
#from whoosh.fields import ID, TEXT, KEYWORD, STORED

import os


def EmptyQuery(model):
    ''' Used to return empty set when whoosh-search results return nothing. '''

    # XXX is this efficient?
    return model.__class__.query.filter('null')


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
                self.index.searcher().search(self.parser.parse(query),
                    limit=limit)]

        if len(results) == 0:
            return EmptyQuery(self.model)

        return self.model.__class__.query.filter(getattr(self.model.__class__,
            self.primary).in_(results))


def whoosh_index(app, model):
    # gets the whoosh index for this model, creating one if it does not exist.
    # in creating one, a schema is created based on the fields of the model.
    # Currently we only support primary key -> whoosh.ID, and sqlalchemy.TEXT
    # -> whoosh.TEXT, but can add more later. A dict of model -> whoosh index
    # is added to the ``app`` variable.

    if not hasattr(app, 'whoosh_indexes'):
        app.whoosh_indexes = {}

    indx = app.whoosh_indexes.get(model.__class__.__name__)

    if indx is None:
        if not app.config.get('WHOOSH_BASE'):
            # XXX todo: is there a better approach to handle the absense of a
            # config value for whoosh base? Should we throw an exception? If
            # so, this exception will be thrown in the after_commit function,
            # which is probably not ideal.

            app.config['WHOOSH_BASE'] = './whoosh_index'

        # we index per model.
        wi = os.path.join(app.config.get('WHOOSH_BASE'),
                model.__class__.__name__)

        schema, primary = _get_whoosh_schema_and_primary(model)

        if whoosh.index.exists_in(wi):
            indx = whoosh.index.open_dir(wi)
        else:
            if not os.path.exists(wi):
                os.makedirs(wi)
            indx = whoosh.index.create_in(wi, schema)

        app.whoosh_indexes[model.__class__.__name__] = indx
        model.__class__.search_query = Searcher(model, primary, indx)

    return indx


def _get_whoosh_schema_and_primary(model):
    schema = {}
    primary = None
    for field in model.__table__.columns:
        if field.primary_key:
            schema[field.name] = whoosh.fields.ID(stored=True, unique=True)
            primary = field.name
        if field.name in model.__searchable__:
            if type(field.type) == sqlalchemy.types.Text:
                schema[field.name] = whoosh.fields.TEXT(
                        analyzer=StemmingAnalyzer())

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
            bytype.setdefault(change[0].__class__.__name__, []).append((update,
                change[0]))

    for values in bytype.itervalues():
        index = whoosh_index(app, values[0][1])
        with index.writer() as writer:
            primary_field = values[0][1].search_query.primary
            searchable = values[0][1].__searchable__

            for update, v in values:
                if update:
                    attrs = dict((key, getattr(v, key)) for key in searchable)
                    attrs[primary_field] = unicode(getattr(v, primary_field))
                    writer.update_document(**attrs)
                else:
                    writer.delete_by_term(primary_field, unicode(getattr(v,
                        primary_field)))


models_committed.connect(after_flush)
