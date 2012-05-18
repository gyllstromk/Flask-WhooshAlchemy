'''

    whooshalchemy flask extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adds whoosh indexing capabilities to SQLAlchemy models for Flask
    applications.

    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''

from __future__ import with_statement
from __future__ import absolute_import


from flask_sqlalchemy import models_committed

import sqlalchemy

from whoosh.qparser import MultifieldParser
from whoosh.analysis import StemmingAnalyzer
import whoosh.index
from whoosh.fields import Schema
#from whoosh.fields import ID, TEXT, KEYWORD, STORED

import heapq
import os


def _EmptyQuery(model):
    ''' Used to return empty set when whoosh-search results return nothing. '''

    # XXX is this efficient?
    return model.__class__.query.filter('null')


class _QueryProxy(sqlalchemy.orm.Query):
    def __init__(self, query_obj, primary_key_name, ws, model, whoosh_rank=None):
        self.__dict__ = query_obj.__dict__.copy()
        self._primary_key_name = primary_key_name
        self._ws = ws
        self.model = model
        self._whoosh_rank = whoosh_rank

    def __iter__(self):
        ''' Reorder ORM-db results according to Whoosh relevance score. '''

        super_iter = super(_QueryProxy, self).__iter__()
        if self._whoosh_rank is None:
            # Whoosh search hasn't been run so behave as normal.

            return super_iter

        # Iterate through the values and re-order by whoosh relevance.
        ordered_by_whoosh_rank = []

        for row in super_iter:
            heapq.heappush(ordered_by_whoosh_rank,
                (self._whoosh_rank[unicode(getattr(row,
                    self._primary_key_name))], row))

        def _inner():
            while ordered_by_whoosh_rank:
                yield heapq.heappop(ordered_by_whoosh_rank)[1]

        return _inner()

    def whoosh_search(self, query):
        results = self._ws(query)

        if len(results) == 0:
            return _EmptyQuery(self.model)

        result_set = set()
        result_ranks = {}

        for rank, result in enumerate(results):
            pk = result[self._primary_key_name]
            result_set.add(pk)
            result_ranks[pk] = rank

        f = self.filter(getattr(self.model.__class__,
            self._primary_key_name).in_(result_set))

        f._whoosh_rank = result_ranks

        return f


class _Searcher(object):
    ''' Assigned to a Model class as ``search_query``, which enables
    text-querying. '''

    def __init__(self, primary, indx):
        self.primary_key_name = primary
        self.index = indx
        self.searcher = indx.searcher()
        fields = set(indx.schema._fields.keys()) - set([self.primary_key_name])
        self.parser = MultifieldParser(list(fields), indx.schema)

    def __call__(self, query, limit=None):
        return self.index.searcher().search(self.parser.parse(query),
                limit=limit)


def _whoosh_index(app, model):
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
            # XXX todo: is there a better approach to handle the absenSe of a
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
        searcher = _Searcher(primary, indx)
        model.__class__.query = _QueryProxy(model.__class__.query, primary,
                searcher, model)

        model.__class__.search_query = searcher

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
        index = _whoosh_index(app, values[0][1])
        with index.writer() as writer:
            primary_field = values[0][1].search_query.primary_key_name
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
