## Installation instructions

This project uses `pyenv` and `pipenv` for managing the python version,
dependencies and even running commands. Python packaging has always been a huge
mess and I hate pretty much everything about it. The recommendation of using
these two tools in combination is from [this blog
post](https://gioele.io/pyenv-pipenv).

### Clone and build monero lmdb

```
git clone https://github.com/monero-project/monero
cd monero/external/db_drivers/liblmdb
make
```

The following environment variables need to be set when installing the
project's dependencies, in particular when installing python lmdb:

```
export LMDB_FORCE_SYSTEM=1
export LMDB_INCLUDEDIR=~/monero/external/db_drivers/liblmdb
export LMDB_LIBDIR=~/monero/external/db_drivers/liblmdb
```

If in doubt, consult this [stackexchange
answer](https://monero.stackexchange.com/questions/12234/python-lmdb-version-mismatch).

### Prepare monero-serialize

Monero-serialize requires local, unpublished patches. For this clone the
repository and checkout the patched branch:

```
git clone https://github.com/TheCharlatan/monero-serialize
cd ~/monero-serialize
git checkout txMetaData
```

### Install pyenv

On ubuntu/debian:

```
sudo apt-get update; sudo apt-get install make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

Then for ease of use: 

```
curl https://pyenv.run | bash
```

Read the manual [here](https://github.com/pyenv/pyenv#basic-github-checkout) on
how to configure the correct environment variables for pyenv.

### Install pipenv

```
pyenv global 3.7.0
pip install pipenv
```

### Install dependencies with pipenv

```
pipenv install ~/monero-serialize
```

## Running the script

The monero lmdb parser requires the following path to be set to the lmdb
libary:

```
LD_LIBRARY_PATH="/usr/local/lib:/home/drgrid/monero/external/db_drivers/liblmdb" \
    pipenv run python main.py --help
```

The help text should self-describe the usage of the parsers. The parsers read
data directly from the blockchain database. The blockchain-parser thus requires
access to the directory where the blockchain database files are located.


### IDE integration

The python path that pipenv is configured to after installation is made
available with:

```
pipenv --py
```

