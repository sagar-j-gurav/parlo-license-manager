from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in parlo_license_manager/__init__.py
from parlo_license_manager import __version__ as version

setup(
	name="parlo_license_manager",
	version=version,
	description="Parlo License Management System for Organizations",
	author="Parlo",
	author_email="admin@parlo.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)