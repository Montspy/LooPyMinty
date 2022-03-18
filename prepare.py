#!/usr/bin/env python3

from dataclasses import dataclass
from pprint import pprint
from typing import TypedDict
from dotenv import load_dotenv
import os, sys
import shutil
import argparse
import asyncio
import json

@dataclass
class Config(dict):
    def __getattr__(self, name):
        if super().__contains__(name):
            return super().__getitem__(name)
        else:
            return None
    def __setattr__(self, name, value):
        return super().__setitem__(name, value)
    def __delattr__(self, name):
        return super().__delitem__(name)
    def __str__(self):
        return super().__str__()
    def __repr__(self):
        return super().__repr__()
        

# Parse CLI arguments
def parse_args(cfg: Config):
    # check for command line arguments
    parser = argparse.ArgumentParser()
    input_grp = parser.add_mutually_exclusive_group(required=True)
    input_grp.add_argument('--file', help='Specify an input file', type=str)
    input_grp.add_argument('--idir', help='Specify an input directory', type=str)
    # parser.add_argument('--odir', help='Specify the output directory (default: idir/output)', type=str)
    parser.add_argument('--metadata', help='Generate metadata templates instead', action='store_true')
    parser.add_argument('--empty', help='Empty the output directory before running', action='store_true')

    args = parser.parse_args()
    
    # Input directory
    if args.file:
        cfg.input_dir, cfg.input_file = os.path.split(args.file)
    elif args.idir:
        cfg.input_dir = os.path.split(os.path.join(args.idir, ''))[0]   # Ensure no trailing '/'
    assert os.path.exists(cfg.input_dir), f'Input file/directory does not exist: {cfg.input_dir}'

    # Empty
    cfg.empty = args.empty

    # Output directory
    cfg.output_dir = './output'
    # cfg.output_dir = os.path.join(os.path.split(cfg.input_dir)[0], 'output') # Create 'output' dir next to cfg.input_dir
    if cfg.empty and os.path.exists(cfg.output_dir):
        if os.path.split(cfg.output_dir)[0] == 'output':
            shutil.rmtree(cfg.output_dir)
    if not os.path.exists(cfg.output_dir):
        os.makedirs(cfg.output_dir)

    # Metadata
    cfg.metadata = args.metadata
    cfg.metadata_path = os.path.join(cfg.output_dir, 'metadata')
    if cfg.metadata and not os.path.exists(cfg.metadata_path):
        os.makedirs(cfg.metadata_path)

    return args

# CID pre-calc helper functions
async def get_file_cid(path: str, version: int=0):
    proc = await asyncio.create_subprocess_shell(
        f'cid --cid-version={version} {path}',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode > 0:
        raise RuntimeError(f'Could not get CIDv{version} of file {path}:\n\t{stderr.decode()}')
    return stdout.decode().strip()

async def get_files_cids(paths: 'list[str]', version: int=0):
    return await asyncio.gather(*[get_file_cid(file, version=version) for file in paths])

def main():
    load_dotenv()
    cfg = Config()
    parse_args(cfg)

    # Get list of files to process
    if cfg.input_file:
        input_files = [cfg.input_file]
    else:
        input_files = next(os.walk(cfg.input_dir))[2]
    
    # Extract ID for all files
    ids = [int('0' + ''.join(filter(str.isdigit, f))) for f in input_files]
    ids = [max(ids) + 1 + i if v == 0 else v for i, v in enumerate(ids)]

    # Sort IDs and files by IDs
    ids, input_files = list(zip(*sorted(zip(ids, input_files))))

    cids = asyncio.run(get_files_cids( [os.path.join(cfg.input_dir, file) for file in input_files] ))
    
    # Output the cids.json file for minter
    if not cfg.metadata:
        print(f'Generating cids.json file in: {cfg.output_dir}')
        cids_path = os.path.join(cfg.output_dir, 'cids.json')
        with open(cids_path, 'w+') as f:
            all_cids = [{'ID': i, 'CID': c} for i,c in zip(ids, cids)]
            json.dump(all_cids, f, indent=4)
    
    # Output metadata template files
    else:
        for id, cid, file in zip(ids, cids, input_files):
            json_file = os.path.splitext(file)[0] + '.json'
            json_path = os.path.join(cfg.metadata_path, json_file)

            token = {
                'image': os.path.join('ipfs://', cid),
                'animation_url': os.path.join('ipfs://', cid),
                'name':  os.getenv('COLLECTION_NAME') or 'COLLECTION_NAME',
                'description':  os.getenv('DESCRIPTION') or 'DESCRIPTION',
                'royalty_percentage': os.getenv('ROYALTY_PERCENTAGE') or 0,
                'tokenId': id,
                'artist': os.getenv('ARTIST') or 'ARTIST',
                'minter': os.getenv('MINTER') or 'MINTER',
                'attributes': [],
                'properties': {}
            }

            print(f'Generating metadata for {file} to {json_path}')

            with open(json_path, 'w+') as f:
                json.dump(token, f, indent=4)

if __name__ == '__main__':
    main()