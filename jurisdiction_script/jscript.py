import warnings
warnings.filterwarnings('ignore')

import glob
import tqdm
import yaml
import fiona
import pickle
import shapely
import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy import signal
import matplotlib.pyplot as plt


def run(config):
    DATA_PATH = r'.\data'
    OUTPUT_PATH = r'.\out'

    jbounds = {}
    pixel_dfs = {'priority': {}, 'feasibility': {}}
    for j in config['jurisdictions']:
        jname = j['name']
        jbfile = j['boundary']
        jbounds[jname] = gpd.read_file('{}\\{}'.format(DATA_PATH, jbfile))
    
    for pixel_type in ['priority', 'feasibility']:
        assert pixel_type in config, f'{pixel_type} not found in config file, exiting'

        pixels_fname = config[pixel_type]['pixels']
        print('Reading in {} pixels...'.format(pixel_type), end=' ', flush=True)
        pixels = gpd.read_file('{}\\{}'.format(DATA_PATH, pixels_fname))
        print('done')

        pixels['centroid'] = pixels.geometry.centroid
        pixels.set_geometry('centroid', inplace=True)
        for k, v in jbounds.items():
            pixels_clipped = gpd.clip(pixels, v.to_crs(pixels.crs))
            pixel_dfs[pixel_type][k] = pixels_clipped

        attributes = config[pixel_type]['attributes']
        print('Joining in attributes:')
        if attributes:
            for att_file in attributes:
                print('\tFrom file {}...'.format(att_file['file']))
                att_data = gpd.read_file('{}\\{}'.format(DATA_PATH, att_file['file']))

                for column in att_file['columns']:
                    col = column['column']
                    name = column['name']
                    join = column['join']
                    assert join in ['binary', 'binary_full', 'numeric', 'nearest', 'popmul', 'max'], "Inappropriate join type specified"
                    
                    print('\t\t{}...'.format(name), end=' ', flush=True)
                    for k in pixel_dfs[pixel_type].keys():
                        if join=='binary':
                            pixel_dfs[pixel_type][k] = join_binary(pixel_dfs[pixel_type][k], att_data, name)
                        elif join=='binary_full':
                            pixel_dfs[pixel_type][k] = join_binary_full(pixel_dfs[pixel_type][k], att_data, name)
                        elif join=='numeric':
                            pixel_dfs[pixel_type][k] = join_numeric(pixel_dfs[pixel_type][k], att_data, col, name)
                        elif join=='nearest':
                            pixel_dfs[pixel_type][k] = join_nearest(pixel_dfs[pixel_type][k], att_data, col, name)
                        elif join=='popmul':
                            pixel_dfs[pixel_type][k] = join_popmul(pixel_dfs[pixel_type][k], att_data, col, 'pop', name)
                        elif join=='max':
                            pixel_dfs[pixel_type][k] = join_max(pixel_dfs[pixel_type][k], att_data, col, name)
                    print('done')

        for k in pixel_dfs[pixel_type].keys():
            pixel_dfs[pixel_type][k].set_geometry('geometry', inplace=True)
            to_drop = ['centroid']
            pixel_dfs[pixel_type][k].drop(columns=to_drop, inplace=True, errors='ignore')

            outfile = "{}\\{}_{}.json".format(OUTPUT_PATH, k, pixel_type)
            print('Saving to {}...'.format(outfile), end=' ', flush=True)
            pixel_dfs[pixel_type][k].to_file(outfile, driver='GeoJSON')
            print('done')

    return


def join_binary_full(left, right, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left.set_geometry('geometry', inplace=True)
    left = gpd.sjoin(left, right2.to_crs(left.crs), how="left")
    left.set_geometry('centroid', inplace=True)
    left.loc[~left.index_right.isnull(), 'index_right'] = 1
    left = left.sort_values('index_right', ascending=False).drop_duplicates('geometry').sort_index()
    left['index_right'].fillna(0, inplace=True)
    left.rename(columns={"index_right": name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


def join_binary(left, right, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left = gpd.sjoin(left, right2.to_crs(left.crs), how="left")
    left.loc[~left.index_right.isnull(), 'index_right'] = 1
    left['index_right'].fillna(0, inplace=True)
    left.rename(columns={"index_right": name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


def join_numeric(left, right, column, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!=column and c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left = gpd.sjoin(left, right2.to_crs(left.crs), how="left")
    left = left.sort_values(column, ascending=False).drop_duplicates('geometry').sort_index()
    left.loc[left['index_right'].isna(), column] = 0
    left.rename(columns={column: name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


def join_nearest(left, right, column, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!=column and c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left = gpd.sjoin_nearest(left, right2.to_crs(left.crs), how="left")
    left = left.sort_values(column, ascending=False).drop_duplicates('geometry').sort_index()
    left.rename(columns={column: name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


def join_popmul(left, right, column, pop_col, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!=column and c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left = gpd.sjoin_nearest(left, right2.to_crs(left.crs), how="left")
    left = left.sort_values(column, ascending=False).drop_duplicates('geometry').sort_index()
    left[name] = left[pop_col]*left[column]
    left.drop(columns=['index_left', 'index_right', column], inplace=True, errors='ignore')
    return left


def join_max(left, right, column, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!=column and c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left.set_geometry('geometry', inplace=True)
    left = left.sjoin(right2.to_crs(left.crs), how='left')
    left.set_geometry('centroid', inplace=True)
    left = left.sort_values(column, ascending=False).drop_duplicates('geometry').sort_index()
    left[column].fillna(0, inplace=True)
    left.rename(columns={column: name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


if __name__=="__main__":
    parser = argparse.ArgumentParser(
                    prog='Jurisdiction Pixel Generator',
                    description='Fills priority and feasibility pixels with attributes based on config file')
    parser.add_argument('config')
    args = parser.parse_args()
    fname = 'config\\{}.yaml'.format(args.config)
    with open(fname, 'rt') as f:
        config = yaml.safe_load(f.read())
    run(config)
