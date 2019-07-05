from setuptools import find_packages, setup

setup(
    name='wdl-lsp',
    author='Broad Institute',
    description='Language Server Protocol (LSP) implementation for Workflow Definition Language (WDL)',
    license='BSD 3-clause "New" or "Revised" License',
    url='https://github.com/broadinstitute/wdl-ide',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Software Development :: Interpreters',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>3.6.0',
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
        'cromwell-tools == 2.2.0',
        'miniwdl == 0.2.2',
        'pygls == 0.8.0',
    ],
    entry_points={
        'console_scripts': ['wdl-lsp = wdl_lsp.__main__:main'],
    },
)