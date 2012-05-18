'''

    whooshalchemy flask extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adds whoosh indexing capabilities to SQLAlchemy models for Flask
    applications.

    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''

from __future__ import absolute_import

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flaskext.testing import TestCase
import flask_whooshalchemy

import datetime
import os
import tempfile
import shutil


class Tests(TestCase):
    def create_app(self):
        tmp_dir = tempfile.mkdtemp()

        config = dict(DATABASE_URL='sqlite://',
                      TESTING=True)

        app = Flask(__name__)
        app.config.update(config)

        app.config['WHOOSH_BASE'] = os.path.join(tmp_dir, 'whoosh')

        app.db = SQLAlchemy(app)

        class BlogishBlob(object):
            __searchable__ = ['title', 'content']

            id = app.db.Column(app.db.Integer, primary_key=True)
            title = app.db.Column(app.db.Text)
            content = app.db.Column(app.db.Text)
            ignored = app.db.Column(app.db.Text)
            created = app.db.Column(app.db.DateTime(), default=datetime.datetime.utcnow())

            def __repr__(self):
                return '{0}(title={1})'.format(self.__class__.__name__, self.title)


        class ObjectA(app.db.Model, BlogishBlob):
            __tablename__ = 'objectA'
            __searchable__ = ['title', 'content']


        class ObjectB(app.db.Model, BlogishBlob):
            __tablename__ = 'objectB'
            __searchable__ = ['title', 'content']

        self.ObjectA = ObjectA
        self.ObjectB = ObjectB

        app.db.create_all()

        return app

    def tearDown(self):
        try:
            shutil.rmtree(self.app.config['WHOOSH_BASE'])
        except OSError, e:
            if e.errno != 2: # code 2 - no such file or directory
                raise

    def test_single_field(self):
        title1 = u'a slightly long title'
        title2 = u'another title'
        title3 = u'wow another title'

        self.app.db.session.add(self.ObjectA(title=title1, content=u'hello world'))
        self.app.db.session.commit()

        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'what'))), 0)
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'title'))), 1)
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'hello'))), 1)

        self.app.db.session.add(self.ObjectB(title=u'my title', content=u'hello world'))
        self.app.db.session.commit()

        # make sure does not interfere with ObjectA's results
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'what'))), 0)
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'title'))), 1)
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'hello'))), 1)

        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'what'))), 0)
        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'title'))), 1)
        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'hello'))), 1)

        self.app.db.session.add(self.ObjectA(title=title2, content=u'a different message'))
        self.app.db.session.commit()

        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'what'))), 0)
        l = list(self.ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 2)

        # ranking should always be as follows, since title2 should have a higher relevance score

        self.assertEqual(l[0].title, title2)
        self.assertEqual(l[1].title, title1)

        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'hello'))), 1)
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'message'))), 1)

        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'what'))), 0)
        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'title'))), 1)
        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'hello'))), 1)
        self.assertEqual(len(list(self.ObjectB.query.whoosh_search(u'message'))), 0)

        self.app.db.session.add(self.ObjectA(title=title3, content=u'a different message'))
        self.app.db.session.commit()

        l = list(self.ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 3)
        self.assertEqual(l[0].title, title2)
        self.assertEqual(l[1].title, title3)
        self.assertEqual(l[2].title, title1)

        self.app.db.session.delete(self.ObjectA.query.get(2))
        self.app.db.session.commit()

        l = list(self.ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0].title, title3)
        self.assertEqual(l[1].title, title1)

        two_days_ago = datetime.date.today() - datetime.timedelta(2)

        title4 = u'a title that is significantly longer than the others'

        self.app.db.session.add(self.ObjectA(title=title4, created=two_days_ago))
        self.app.db.session.commit()

        one_day_ago = datetime.date.today() - datetime.timedelta(1)

        recent = list(self.ObjectA.query.whoosh_search(u'title')
                .filter(self.ObjectA.created >= one_day_ago))

        self.assertEqual(len(recent), 2)
        self.assertEqual(l[0].title, title3)
        self.assertEqual(l[1].title, title1)

        three_days_ago = datetime.date.today() - datetime.timedelta(3)

        l = list(self.ObjectA.query.whoosh_search(u'title')
                .filter(self.ObjectA.created >= three_days_ago))

        self.assertEqual(len(l), 3)
        self.assertEqual(l[0].title, title3)
        self.assertEqual(l[1].title, title1)
        self.assertEqual(l[2].title, title4)

        title5 = u'title with title as frequent title word'

        self.app.db.session.add(self.ObjectA(title=title5))
        self.app.db.session.commit()

        l = list(self.ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 4)
        self.assertEqual(l[0].title, title5)
        self.assertEqual(l[1].title, title3)
        self.assertEqual(l[2].title, title1)
        self.assertEqual(l[3].title, title4)

        # test limit
        l = list(self.ObjectA.query.whoosh_search(u'title', limit=2))
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0].title, title5)
        self.assertEqual(l[1].title, title3)

    def test_multi_field(self):
        title1 = u'my title'
        self.app.db.session.add(self.ObjectA(title=title1, content=u'hello world'))
        self.app.db.session.commit()

        l = list(self.ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 1)

        l = list(self.ObjectA.query.whoosh_search(u'hello'))
        self.assertEqual(len(l), 1)

        l = list(self.ObjectA.query.whoosh_search(u'title', fields=('title',)))
        self.assertEqual(len(l), 1)
        l = list(self.ObjectA.query.whoosh_search(u'hello', fields=('title',)))
        self.assertEqual(len(l), 0)

        l = list(self.ObjectA.query.whoosh_search(u'title', fields=('content',)))
        self.assertEqual(len(l), 0)
        l = list(self.ObjectA.query.whoosh_search(u'hello', fields=('content',)))
        self.assertEqual(len(l), 1)

        l = list(self.ObjectA.query.whoosh_search(u'hello dude', fields=('content',), or_=True))
        self.assertEqual(len(l), 1)

        l = list(self.ObjectA.query.whoosh_search(u'hello dude', fields=('content',), or_=False))
        self.assertEqual(len(l), 0)

    def test_chaining(self):
        self.app.db.session.add(self.ObjectA(title=u'title one', content=u'a poem'))
        self.app.db.session.add(self.ObjectA(title=u'title two', content=u'about testing'))
        self.app.db.session.add(self.ObjectA(title=u'title three', content=u'is delightfully tested'))
        self.app.db.session.add(self.ObjectA(title=u'four', content=u'tests'))
        self.app.db.session.commit()

        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'title'))), 3)
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'test'))), 3)

        # chained query, operates as AND
        self.assertEqual(len(list(self.ObjectA.query.whoosh_search(u'title').whoosh_search(u'test'))),
                2)

#         self.assertEqual(len(recent), 1)
#         self.assertEqual(recent[0].title, b.title)
#         old = list(self.ObjectA.search_query(u'good').filter(self.ObjectA.created <= datetime.date.today() - datetime.timedelta(1)))
#         self.assertEqual(len(old), 1)
#         self.assertEqual(old[0].title, a.title)


if __name__ == '__main__':
    import unittest
    unittest.main()
