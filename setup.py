from setuptools import setup, find_packages


def read(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except IOError:
        return ''


setup(
    name='reqcli',
    version='0.0.1',
    description='A scraping/API client framework with builtin caching and things and stuff',
    long_description=read('README.md'),
    author='shiftinv',
    url='https://github.com/shiftinv/reqcli',
    license='Apache 2.0',
    packages=find_packages(exclude=['tests*']),
    install_requires=read('requirements.txt').splitlines(),
    extras_require={
        'dev': ['pytest', 'pytest-cov', 'requests-mock']
    },
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
    ]
)
