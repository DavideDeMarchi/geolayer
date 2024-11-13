from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='geolayer',
   version='0.0.3',
   description='TODO short description',
   license="TODO",
   long_description=long_description,
   author='TODO',
   author_email='TODO',
   url="TODO",
   packages=['geolayer'],
   install_requires=['wheel',],
)