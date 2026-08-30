import codecs
import os
import re

# Always prefer setuptools over distutils
from setuptools import setup, find_namespace_packages


setup(name="compass_metrics_model",
      description="Metrics Model",
      url="https://github.com/open-metrics-code/compass-metrics-model",
      version="0.1.0",
      author="Chenqi Shan, Yehui Wang",
      author_email="chenqishan337@gmail.com",
      license="GPLv3",
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Software Development',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5'],
      keywords="Metric Model",
      # 仓库内大量包目录（compass_metrics_v2、compass_model_v2 的子包、
      # compass_metrics/constants、compass_model 的子包等）没有 __init__.py，
      # 属于 PEP 420 命名空间包，必须用 find_namespace_packages 才能打进发行包
      packages=find_namespace_packages(include=['compass_common*', 'compass_contributor*',
                                                'compass_metrics*', 'compass_model*',
                                                'compass_prediction*']),
      package_data={
          'compass_metrics_model': ['resources/*'],
          'compass_metrics': ['resources/*'],
          'compass_contributor': ['conf_utils/*']
      },
      python_requires='>=3.4',
      setup_requires=['wheel'],
      zip_safe=False
      )
