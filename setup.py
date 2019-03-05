from setuptools import setup

setup(name='graph_minimap',
      version='0.0.1',
      description='Rough graph minimap',
      url='http://github.com/uio-bmi/graph_minimap',
      author='Ivar Grytten and Knut Rand',
      author_email='',
      license='MIT',
      zip_safe=False,
      install_requires=['numpy', 'python-coveralls', 'numba', 'pathos', 'sortedcontainers',
                        'pyfaidx', 'scikit-bio', 'tqdm'],
      classifiers=[
            'Programming Language :: Python :: 3'
      ],
      entry_points={
            'console_scripts': ['graph_minimap=graph_minimap.map:map_all',
                                'graph_minimap_index=graph_minimap.index:main'],
      }
)
