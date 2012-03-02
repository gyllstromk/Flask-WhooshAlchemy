Flask-WhooshAlchemy extension
===================

ALPHA but actively developed.

Supports the easy text-indexing of SQLAlchemy model fields.

BSD license

Quick start example
-----

>>> import flask_whooshalchemy
>>>
>>> db = SQLAlchemy(app)  # see flask-sqlalchemy
>>>
>>> class BlogPost(db.Model):
...   __tablename__ = 'blogpost'
...   __searchable__ = ['title', 'body']  # these fields will be indexed by whoosh
...
...   id = app.db.Column(app.db.Integer, primary_key=True)
...   title = app.db.Column(app.db.Text)
...   content = app.db.Column(app.db.Text)
...   created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
...
...   def __repr__(self):
...       return '{0}(title={1})'.format(self.__class__.__name__, self.title)
...
>>> app.config['WHOOSH_BASE'] = 'path/to/whoosh/base'
>>> m = BlogPost(title='My cool title', content='This is the first post.')
>>> db.session.add(m); db.session.commit()
>>>
>>> print list(BlogPost.search_query('cool'))
... [BlogPost(title='My cool title')]
>>> print list(BlogPost.search_query('first'))
... [BlogPost(title='My cool title')]
>>>
>>> # Note: the response is a :class:`BaseQuery` object, so you can append other SQL operations:
>>>
>>> two_days_ago = datetime.date.today() - datetime.timedelta(2)
>>> recent_matches = BlogPost.search_query('first').filter(BlogPost.created >= two_days_ago)
