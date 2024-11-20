from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='geolayer',
   version='0.0.3',
   description='Geospatial data visualization',
   license="EUPL1.2",
   long_description=long_description,
   author='Davide De Marchi',
   author_email='Davide.DE-MARCHI@ec.europa.eu',
   url="https://geolayer.readthedocs.io/en/latest/",
   packages=['geolayer'],
   install_requires=['wheel',],
)