from setuptools import setup, find_packages

setup(
    name='StatsCalc',
    version='1.0',
    py_modules=['statscalc'],
    package_dir={'': 'src'}, 
    include_package_data=True,
    install_requires=[
        'click',
    ],
    entry_points={
        'console_scripts': [
            'statscalc = statscalc:cli'
        ],
    },
)
