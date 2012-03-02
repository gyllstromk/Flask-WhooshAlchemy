"""
Flask-WhooshAlchemy
-------------

Whoosh extension to Flask/SQLAlchemy
"""
from setuptools import setup


setup(
    name='Flask-WhooshAlchemy',
    version='0.1a',
    url='https://github.com/gyllstromk/Flask-WhooshAlchemy',
    license='BSD',
    author='Karl Gyllstrom',
    author_email='karl.gyllstrom+code@gmail.com',
    description='Whoosh extension to Flask/SQLAlchemy',
    long_description=__doc__,
    py_modules=['flask_whooshalchemy'],
    # if you would be using a package instead use packages instead
    # of py_modules:
    # packages=['flask_sqlite3'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask', 'Flask-SQLAlchemy', 'whoosh'
    ],
    classifiers=[
        #'Environment :: Web Environment',
        #'Intended Audience :: Developers',
        #'License :: OSI Approved :: BSD License',
        #'Operating System :: OS Independent',
        #'Programming Language :: Python',
        #'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        #'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
