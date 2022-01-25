## Installation instructions

This project uses `pyenv` and `pipenv` to manage python version and dependencies and run commands.

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

### Running the 


