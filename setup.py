import setuptools


name = 'celery-worker-on-demand'
version = '0.1.0'

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name=name,
    version=version,
    author='Ilhasoft\'s Web Team',
    author_email='contato@ilhasoft.com.br',
    description='Up and down Celery workers on demand.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Ilhasoft/celery-worker-on-demand',
    packages=['celery_worker_on_demand'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'celery>=4.2.1',
        'cached-property>=1.5.1',
    ],
    python_requires='>=3.4',
)
