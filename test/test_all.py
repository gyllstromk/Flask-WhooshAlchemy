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
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.testing import TestCase
import flask.ext.whooshalchemy as wa

import datetime
import os
import tempfile
import shutil


db = SQLAlchemy()


class BlogishBlob(object):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    content = db.Column(db.String)
    blurb = db.Column(db.Unicode)
    ignored = db.Column(db.Unicode)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow())

    def __repr__(self):
        return '{0}(title={1})'.format(self.__class__.__name__, self.title)


def _after_flush(app, changes):
    from sqlalchemy.orm import EXT_CONTINUE
    return EXT_CONTINUE


class ObjectA(db.Model, BlogishBlob):
    __tablename__ = 'objectA'
    __searchable__ = ['title', 'content', 'blurb']


class ObjectB(db.Model, BlogishBlob):
    __tablename__ = 'objectB'
    __searchable__ = ['title', 'content', 'content']  # dup intentional


class ObjectC(db.Model, BlogishBlob):
    __tablename__ = 'objectC'
    __searchable__ = ['title', 'field_that_doesnt_exist']


class Tests(TestCase):
    DATABASE_URL = 'sqlite://'
    TESTING = True

    def create_app(self):
        tmp_dir = tempfile.mkdtemp()

        app = Flask(__name__)

        app.config['WHOOSH_BASE'] = os.path.join(tmp_dir, 'whoosh')
        db.init_app(app)

        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        try:
            pass
            #shutil.rmtree(self.app.config['WHOOSH_BASE'])
        except OSError as e:
            if e.errno != 2:  # code 2 - no such file or directory
                raise

        db.session.remove()
        db.drop_all()

    def test_flask(self):
        """Used to fail due to a bug in Flask-SQLAlchemy."""
        from flask.ext.sqlalchemy import before_models_committed, models_committed
        
        before_models_committed.connect(_after_flush)
        models_committed.connect(_after_flush)
        db.session.add(ObjectB(title=u'my title', content=u'hello world'))
        db.session.add(ObjectA(title=u'a title', content=u'hello world'))
        db.session.flush()
        db.session.commit()

    def test_add_entry(self):
        db.session.add(ObjectA(title=u'title', blurb='this is a blurb'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search('blurb').count(), 1)

    def test_simple_search(self):
        db.session.add(
            ObjectA(
                title=u'a slightly long title',
                content=u'hello world'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search('what').count(), 0)
        self.assertEqual(ObjectA.query.whoosh_search(u'no match').count(), 0)
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 1)
        self.assertEqual(ObjectA.query.whoosh_search(u'hello').count(), 1)

    def test_conflict_fails(self):
        db.session.add(ObjectB(title=u'my title', content=u'hello world'))
        db.session.commit()

        db.session.add(ObjectC(title=u'my title', content=u'hello world'))
        self.assertRaises(AttributeError, db.session.commit)

    def test_tables_dont_interfere(self):
        db.session.add(
            ObjectA(
                title=u'a slightly long title',
                content=u'hello world'))
        db.session.add(ObjectB(title=u'what title', content=u'hello world'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'what').count(), 0)
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 1)

        self.assertEqual(ObjectB.query.whoosh_search(u'what').count(), 1)
        self.assertEqual(ObjectB.query.whoosh_search(u'title').count(), 1)

    def test_search_multiple_rows(self):
        db.session.add(
            ObjectA(
                title=u'a slightly long title',
                content=u'hello world'))
        db.session.add(
            ObjectA(title='another title', content=u'a different message'))
        db.session.add(
            ObjectA(
                title="ceci n'est pas un titre",
                content='yet another message'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 2)

    def bad_all(self):
        title1 = u'a slightly long title'
        title2 = u'another title'
        title3 = u'wow another title'

        obj2 = ObjectA(title=title2, content=u'a different message')
        db.session.add(obj2)
        db.session.commit()

        self.assertEqual(len(list(ObjectA.query.whoosh_search(u'what'))), 0)
        l = list(ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 2)

        # ranking should always be as follows, since title2 should have a higher relevance score

        self.assertEqual(l[0].title, title2)
        self.assertEqual(l[1].title, title1)

        self.assertEqual(len(list(ObjectA.query.whoosh_search(u'hello'))), 1)
        self.assertEqual(len(list(ObjectA.query.whoosh_search(u'message'))), 1)

        self.assertEqual(len(list(ObjectB.query.whoosh_search(u'what'))), 0)
        self.assertEqual(len(list(ObjectB.query.whoosh_search(u'title'))), 1)
        self.assertEqual(len(list(ObjectB.query.whoosh_search(u'hello'))), 1)
        self.assertEqual(len(list(ObjectB.query.whoosh_search(u'message'))), 0)

        db.session.add(ObjectA(title=title3, content=u'a different message'))
        db.session.commit()

        l = list(ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 3)
        self.assertEqual(l[0].title, title2)
        self.assertEqual(l[1].title, title3)
        self.assertEqual(l[2].title, title1)

        db.session.delete(obj2)
        db.session.commit()

        l = list(ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0].title, title3)
        self.assertEqual(l[1].title, title1)

        two_days_ago = datetime.date.today() - datetime.timedelta(2)

        title4 = u'a title that is significantly longer than the others'

        db.session.add(ObjectA(title=title4, created=two_days_ago))
        db.session.commit()

        one_day_ago = datetime.date.today() - datetime.timedelta(1)

        recent = list(ObjectA.query.whoosh_search(u'title')
                .filter(ObjectA.created >= one_day_ago))

        self.assertEqual(len(recent), 2)
        self.assertEqual(l[0].title, title3)
        self.assertEqual(l[1].title, title1)

        three_days_ago = datetime.date.today() - datetime.timedelta(3)

        l = list(ObjectA.query.whoosh_search(u'title')
                .filter(ObjectA.created >= three_days_ago))

        self.assertEqual(len(l), 3)
        self.assertEqual(l[0].title, title3)
        self.assertEqual(l[1].title, title1)
        self.assertEqual(l[2].title, title4)

        title5 = u'title with title as frequent title word'

        db.session.add(ObjectA(title=title5))
        db.session.commit()

        l = list(ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 4)
        self.assertEqual(l[0].title, title5)
        self.assertEqual(l[1].title, title3)
        self.assertEqual(l[2].title, title1)
        self.assertEqual(l[3].title, title4)

        # test limit
        l = list(ObjectA.query.whoosh_search(u'title', limit=2))
        self.assertEqual(len(l), 2)
        self.assertEqual(l[0].title, title5)
        self.assertEqual(l[1].title, title3)

        # XXX should replace this with a new function, but I can't figure out
        # how to do this cleanly with flask sqlalchemy and testing

        db.drop_all()
        db.create_all()

        title1 = u'my title'
        db.session.add(ObjectA(title=title1, content=u'hello world'))
        db.session.commit()

        l = list(ObjectA.query.whoosh_search(u'title'))
        self.assertEqual(len(l), 1)

        l = list(ObjectA.query.whoosh_search(u'hello'))
        self.assertEqual(len(l), 1)

        l = list(ObjectA.query.whoosh_search(u'title', fields=('title',)))
        self.assertEqual(len(l), 1)
        l = list(ObjectA.query.whoosh_search(u'hello', fields=('title',)))
        self.assertEqual(len(l), 0)

        l = list(ObjectA.query.whoosh_search(u'title', fields=('content',)))
        self.assertEqual(len(l), 0)
        l = list(ObjectA.query.whoosh_search(u'hello', fields=('content',)))
        self.assertEqual(len(l), 1)

        l = list(ObjectA.query.whoosh_search(u'hello dude', fields=('content',), or_=True))
        self.assertEqual(len(l), 1)

        l = list(ObjectA.query.whoosh_search(u'hello dude', fields=('content',), or_=False))
        self.assertEqual(len(l), 0)

        # new function: test chaining
        db.drop_all()
        db.create_all()

        db.session.add(ObjectA(title=u'title one', content=u'a poem'))
        db.session.add(ObjectA(title=u'title two', content=u'about testing'))
        db.session.add(ObjectA(title=u'title three', content=u'is delightfully tested'))
        db.session.add(ObjectA(title=u'four', content=u'tests'))
        db.session.commit()

        self.assertEqual(len(list(ObjectA.query.whoosh_search(u'title'))), 3)
        self.assertEqual(len(list(ObjectA.query.whoosh_search(u'test'))), 3)

        # chained query, operates as AND
        self.assertEqual(len(list(ObjectA.query.whoosh_search(u'title').whoosh_search(u'test'))),
                2)


#         self.assertEqual(len(recent), 1)
#         self.assertEqual(recent[0].title, b.title)
#         old = list(ObjectA.search_query(u'good').filter(ObjectA.created <= datetime.date.today() - datetime.timedelta(1)))
#         self.assertEqual(len(old), 1)
#         self.assertEqual(old[0].title, a.title)


if __name__ == '__main__':
    import unittest
    unittest.main()
