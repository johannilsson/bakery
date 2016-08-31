from setuptools import setup

setup(name='bakery',
      version='0.4-dev',
      description='Another static site generator',
      url='http://github.com/johannilsson/bakery',
      author='Johan Nilsson',
      author_email='johan@markupartist.com',
      license='MIT',
      packages=['bakery'],
      install_requires=[
          'Markdown',
          'PIL',
          'PyYAML',
          'pystache',
          'smartypants',
          'yuicompressor'
      ],
      zip_safe=False,
      entry_points={
          'console_scripts': ['bakery=bakery.bakery:main'],
      }
)

