from setuptools import setup, find_packages

setup(name='pyrfidhid',
      version='0.1',
      description='Library to control 125Khz RFID USB HID Device',
      url='https://github.com/charlysan/pyrfidhid/',
      author='charlysan',
      author_email='chrlysn0@gmail.com',
      license='MIT',
      packages=find_packages(),
      install_requires=['pyusb ~= 1.0'])
