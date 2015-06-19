Welcome to Flask-WhooshAlchemy!
===============================

Flask-WhooshAlchemy is a Flask extension that integrates the text-search functionality of `Whoosh <https://bitbucket.org/mchaput/whoosh/wiki/Home>`_ with the ORM of `SQLAlchemy <http://www.sqlalchemy.org/>`_ for use in `Flask <http://flask.pocoo.org/>`_ applications.

Source code and issue tracking at `GitHub <http://github.com/gyllstromk/Flask-WhooshAlchemy>`_.

View the official docs at http://packages.python.org/Flask-WhooshAlchemy/.

Install
-------

::

    pip install flask_whooshalchemy

Or:

::
    
    git clone https://github.com/gyllstromk/Flask-WhooshAlchemy.git

Quickstart
----------

Let's set up the environment and create our model:

::

    import flask.ext.whooshalchemy

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

Let's create a post:

::

    db.session.add(
        BlogPost(title='My cool title', content='This is the first post.')
    ); db.session.commit()

After the session is committed, our new ``BlogPost`` is indexed. Similarly, if the post is deleted, it will be removed from the Whoosh index.

Text Searching
--------------

To execute a simple search:

::

    results = BlogPost.query.whoosh_search('cool')

This will return all ``BlogPost`` instances in which at least one indexed field (i.e., 'title' or 'content') is a text match to the query. Results are ranked according to their relevance score, with the best match appearing first when iterating. The result of this call is a (subclass of) :class:`sqlalchemy.orm.query.Query` object, so you can chain other SQL operations. For example::

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
