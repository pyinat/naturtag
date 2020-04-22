from setuptools import setup, find_packages

setup(
    name='taxon-keyword-gen',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
        'pandas',
        'progress',
        # Switch back to upstream package if/when PR is merged
        # 'pyinaturalist',
        "https://github.com/JWCook/pyinaturalist.git",
        # 'python-xmp-toolkit',
        'requests',
        'requests-ftp',
    ],
    entry_points={
        'console_scripts': [
            'taxgen-inat=taxgen.inat_export:main',
            'taxgen-ncbi=taxgen.ncbi_export:main',
        ],
    }
)
