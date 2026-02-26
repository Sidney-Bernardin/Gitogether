#!/bin/bash

IFS=$'\n'
for l in $(git ls-tree -rlt HEAD)
do
    filename=$(echo $l | cut -f 2)
    x=$(echo $l | cut -f 1 | tr -s ' ' '\t')
    echo "$x"
done
