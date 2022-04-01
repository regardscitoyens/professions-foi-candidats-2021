#!/bin/bash

cd $(dirname $0)/..
cd documents
mkdir -p PR22
cd PR22
mkdir -p T1 T2
cd T1
curl https://www.cnccep.fr/candidats.html       |
 grep '/Candidat-'                              |
 sed -r 's/^.*(src|href)="\.([^"]+)".*$/\2/'    |
 while read url; do
  wget https://www.cnccep.fr$url
 done
