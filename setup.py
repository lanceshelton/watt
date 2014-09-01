from distutils.core import setup

description='A live midi sequencer input for the Digitech Whammy'
setup(
    name='Watt',
    version='0.1.0',
    author='Lance Shelton',
    author_email='notarealemailaddress@notarealdomain.com',
    packages=['watt', 'watt.banks'],
    scripts=[],
    url='https://github.com/lanceshelton/Watt/',
    license='LICENSE.txt',
    description=description,
    long_description=description,
)
