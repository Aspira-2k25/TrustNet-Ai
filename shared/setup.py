from setuptools import setup, find_packages
setup(
    name='trustnet-shared',
    version='0.1.0',
    packages=['shared'] + ['shared.' + p for p in find_packages(where='.')],
    package_dir={'shared': '.'}
)