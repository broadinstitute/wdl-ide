import os

from setuptools import find_packages, setup

cwd = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(cwd, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='wdl-lsp',
    author='Broad Institute',
    description='Language Server Protocol (LSP) implementation for Workflow Definition Language (WDL)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='BSD 3-clause "New" or "Revised" License',
    url='https://github.com/broadinstitute/wdl-ide',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Software Development :: Interpreters',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.8',
    packages=find_packages(
        exclude=[
            'tests',
        ],
    ),
    setup_requires=[
        'setuptools_scm',
    ],
    use_scm_version={
        'root': '..',
        'relative_to': __file__,
    },
    install_requires=[
        'cromwell-tools >= 2.4.1',
        'miniwdl >= 1.11.1',
        'pygls >= 1.3.1',
    ],
    entry_points={
        'console_scripts': ['wdl-lsp = wdl_lsp.__main__:main'],
    },
)