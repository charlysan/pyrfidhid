from setuptools import setup, find_packages

setup(name='pyrfidhid',
      version='0.2',
      description='Library to control 125Khz RFID USB HID Device',
      url='https://github.com/charlysan/pyrfidhid/',
      # scripts=['cli/rfid_cli.py'],
      entry_points={
        'console_scripts': [
            'rfid_cli = cli.rfid_cli:main'
        ]
      },
      author='charlysan',
      author_email='chrlysn0@gmail.com',
      license='MIT',
      packages=find_packages(),
      install_requires=['pyusb ~= 1.0', 'mock ~= 2.0'])
