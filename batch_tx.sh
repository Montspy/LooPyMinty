#!/usr/bin/env bash

for i in $(cat tx_list.txt); do
    id=$(echo $i | awk -F':' '{print $1}')
    to=$(echo $i | awk -F':' '{print $2}')
    echo "Transferring $id to $to..."
    if [ ! -z $1 ]; then
        echo "./docker.sh transfer -n 1 --nft $id --to $to --noprompt"
    else
        ./docker.sh transfer -n 1 --nft $id --to $to --noprompt
    fi
    echo
done