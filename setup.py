import os
import sys
import sysconfig
from setuptools import setup

site_packages = os.path.relpath(sysconfig.get_path("purelib"), sys.prefix)

setup(
    data_files=[(site_packages, ["norn-autoload.pth"])],
)
