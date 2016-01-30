Welcome to Flask-WhooshAlchemyPlus!
===============================

Flask-WhooshAlchemyPlus is a Flask extension that integrates the text-search functionality of `Whoosh <https://bitbucket.org/mchaput/whoosh/wiki/Home>`_ with the ORM of `SQLAlchemy <http://www.sqlalchemy.org/>`_ for use in `Flask <http://flask.pocoo.org/>`_ applications.

Source code and issue tracking at `GitHub <https://github.com/Revolution1/Flask-WhooshAlchemyPlus>`_.


Install
-------

::

    $ pip install flask_whooshalchemyplus

Or:

::

    $ git clone https://github.com/Revolution1/Flask-WhooshAlchemyPlus.git
    $ cd Flask-WhooshAlchemyPlus && python setup.py install

Quickstart
----------

Let's set up the environment and create our model:

::

    import flask_whooshalchemyplus

    # set the location for the whoosh index
    app.config['WHOOSH_BASE'] = 'path/to/whoosh/base'


    class BlogPost(db.Model):
      __tablename__ = 'blogpost'
      __searchable__ = ['title', 'content']  # these fields will be indexed by whoosh
      __analyzer__ = SimpleAnalyzer()        # configure analyzer; defaults to
                                             # StemmingAnalyzer if not specified

      id = app.db.Column(app.db.Integer, primary_key=True)
      title = app.db.Column(app.db.Unicode)  # Indexed fields are either String,
      content = app.db.Column(app.db.Text)   # Unicode, or Text
      created = db.Column(db.DateTime, default=datetime.datetime.utcnow)

Only two steps to get started:

1) Set the ``WHOOSH_BASE`` to the path for the whoosh index. If not set, it will default to a directory called 'whoosh_index' in the directory from which the application is run.
2) Add a ``__searchable__`` field to the model which specifies the fields (as ``str`` s) to be indexed .
3) set ``WHOOSH_DISABLED`` to ``True`` to disable whoosh indexing .

Let's create a post:

::

    db.session.add(
        BlogPost(title='My cool title', content='This is the first post.')
    ); db.session.commit()

After the session is committed, our new ``BlogPost`` is indexed. Similarly, if the post is deleted, it will be removed from the Whoosh index.


Manually Indexing
-----------------

By defualt records can be indexed only when the server is running.
So if you want to index them manually:

::

    from flask_whooshalchemyplus import index_all

    index_all(app)


Text Searching
--------------

To execute a simple search:

::

    results = BlogPost.query.whoosh_search('cool')

This will return all ``BlogPost`` instances in which at least one indexed field (i.e., 'title' or 'content') is a text match to the query. Results are ranked according to their relevance score, with the best match appearing first when iterating. The result of this call is a (subclass of) ``sqlalchemy.orm.query.Query`` object, so you can chain other SQL operations. For example::

    two_days_ago = datetime.date.today() - datetime.timedelta(2)
    recent_matches = BlogPost.query.whoosh_search('first').filter(
        BlogPost.created >= two_days_ago)

Or, in alternative (likely slower) order::

    recent_matches = BlogPost.query.filter(
        BlogPost.created >= two_days_ago).whoosh_search('first')

We can limit results::

    # get 2 best results:
    results = BlogPost.query.whoosh_search('cool', limit=2)

By default, the search is executed on all of the indexed fields as an OR conjunction. For example, if a model has 'title' and 'content' indicated as ``__searchable__``, a query will be checked against both fields, returning any instance whose title or content are a content match for the query. To specify particular fields to be checked, populate the ``fields`` parameter with the desired fields::

    results = BlogPost.query.whoosh_search('cool', fields=('title',))

By default, results will only be returned if they contain all of the query terms (AND). To switch to an OR grouping, set the ``or_`` parameter to ``True``::

    results = BlogPost.query.whoosh_search('cool', or_=True)


If you want ordinary text matching result too::

    results =  BlogPost.query.whoosh_search('cool', like=True)

This acts like whoosh_search('cool') + SQL LIKE '%cool%'


pure_whoosh
------------------

If you want the ``whoosh.index.searcher().search()`` result::

    results =  BlogPost.pure_whoosh(self, query, limit=None, fields=None, or_=False)


CHANGELOG
---------

- v0.7.4 :

  - Feature: add fuzzy-searching using SQL LIKE

- v0.7.3 :

  - Fix: Chinese analyzer does not take affect

- v0.7.2 :

  - Fix: index_all cannot detect indexable models by itself

- v0.7.1 :

  - Feature: Indexing child module class `github issue #43 <https://github.com/gyllstromk/Flask-WhooshAlchemy/pull/43>`_
  - Feature: Add python3 supprot
  - Fix: Obey result sorting if caller explicitly uses order_by() on query `github pull request #32 <https://github.com/gyllstromk/Flask-WhooshAlchemy/pull/32/files>`_
  - Fix: custom query_class usage `github pull request #35 <https://github.com/gyllstromk/Flask-WhooshAlchemy/pull/35/files>`_
  - Feature: add ``WHOOSH_DISABLED`` option to disable whooshalchemyplus at runtime

