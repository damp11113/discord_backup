from setuptools import setup, find_packages

setup(
    name='discord_backup',
    version='2022.4.23.3.3',
    license='MIT',
    author='damp11113',
    author_email='damp51252@gmail.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='https://github.com/damp11113/discord_backup',
    description='read on https://github.com/damp11113/discord_backup',
    install_requires=[
        'damp11113',
        'discord.py'
    ]
)