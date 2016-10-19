"""
Flask-WhooshAlchemy
-------------

Whoosh extension to Flask/SQLAlchemy
"""

from setuptools import setup
import os


setup(
    name='Flask-WhooshAlchemy',
    version='0.8',
    url='https://github.com/gyllstromk/Flask-WhooshAlchemy',
    license='BSD',
    author='Karl Gyllstrom',
    author_email='karl.gyllstrom+code@gmail.com',
    description='Whoosh extension to Flask/SQLAlchemy',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),

    py_modules=['flask_whooshalchemy'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[x.strip() for x in
        open(os.path.join(os.path.dirname(__file__),
            'requirements.txt'))],
    tests_require=['Flask-Testing'],

    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    test_suite='test.test_all',
)
