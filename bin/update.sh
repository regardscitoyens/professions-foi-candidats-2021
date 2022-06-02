#!/bin/bash

cd $(echo $0 | sed 's#/[^/]*$##')/..
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"    # if `pyenv` is not already on PATH
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
pyenv activate proffoi

git pull > /tmp/load_prof_foi.tmp 2>&1

bin/scrap.py LG22 >> /tmp/load_prof_foi.tmp 2>&1

if git status | grep "documents/" > /dev/null; then
  cat /tmp/load_prof_foi.tmp
  git add documents
  git commit -m "autoupdate"
  git push
fi
