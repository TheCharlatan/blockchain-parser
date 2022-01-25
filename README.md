## Installation instructions

This project uses `pyenv` and `pipenv` for managing the python version,
dependencies and even running commands. The recommendation of using these two
tools in combination is from [this blog post](https://gioele.io/pyenv-pipenv).

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

### Install pyenv and pipenv

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
how to configure the correct shell path and environment.

Install pipenv:

```
sudo apt install pipenv
```

### Install dependencies with pipenv

```
pipenv install 
```

Monero-serialize requires local, unpublished patches. For this clone the
repository:

```
git clone https://github.com/TheCharlatan/monero-serialize
```

And install it with:

```
pipenv install ~/monero-serialize
```

### Running the binary

The monero lmdb parser requires the following path to be set to the lmdb
libary:

```
LD_LIBRARY_PATH="/usr/local/lib:/home/drgrid/monero/external/db_drivers/liblmdb pipenv run python monero_parser.py"
```


