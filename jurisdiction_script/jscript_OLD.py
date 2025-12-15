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
    county = config['county']
    city = config['city']
    jbounds = gpd.read_file('{}\\{}'.format(DATA_PATH, config['boundary']))
    
    for pixel_type in ['priority', 'feasibility']:
        assert pixel_type in config, f'{pixel_type} not found in config file, exiting'

        pixels_fname = config[pixel_type]['pixels']
        print('Reading in {} pixels...'.format(pixel_type), end=' ', flush=True)
        pixels = gpd.read_file('{}\\{}'.format(DATA_PATH, pixels_fname))
        print('done')

        pixels['centroid'] = pixels.geometry.centroid
        pixels.set_geometry('centroid', inplace=True)
        pixels = gpd.clip(pixels, jbounds.to_crs(pixels.crs))

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
                    assert join in ['binary', 'numeric', 'nearest', 'popmul', 'max'], "Inappropriate join type specified"
                    
                    print('\t\t{}...'.format(name), end=' ', flush=True)
                    if join=='binary':
                        pixels = join_binary(pixels, att_data, name)
                    elif join=='numeric':
                        pixels = join_numeric(pixels, att_data, col, name)
                    elif join=='nearest':
                        pixels = join_nearest(pixels, att_data, col, name)
                    elif join=='popmul':
                        pixels = join_popmul(pixels, att_data, col, 'pop', name)
                    elif join=='max':
                        pixels = join_max(pixels, att_data, col, name)
                    print('done')

        pixels.set_geometry('geometry', inplace=True)
        to_drop = ['centroid']
        pixels.drop(columns=to_drop, inplace=True, errors='ignore')

        outfile = "{}\\{}_{}_{}.json".format(OUTPUT_PATH, county, city, pixel_type)
        print('Saving to {}...'.format(outfile), end=' ', flush=True)
        pixels.to_file(outfile, driver='GeoJSON')
        print('done')

    return


def join_binary(left, right, name):
    right = gpd.GeoDataFrame(right)
    left = gpd.sjoin(left, right.to_crs(left.crs), how="left")
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
    left.loc[left['index_right'].isna(), column] = 0
    left.rename(columns={column: name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


def join_nearest(left, right, column, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!=column and c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left = gpd.sjoin_nearest(left, right2.to_crs(left.crs), how="left")
    left.rename(columns={column: name}, inplace=True)
    left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
    return left


def join_popmul(left, right, column, pop_col, name):
    right = gpd.GeoDataFrame(right)
    to_drop = [c for c in right.columns if c!=column and c!='geometry']
    right2 = right.drop(columns=to_drop, errors='ignore')
    left = gpd.sjoin_nearest(left, right2.to_crs(left.crs), how="left")
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


def old():
    pop_mfre = gpd.read_file(r"C:\Users\ariba\Documents\GSR\EV Equity\savio\data\pop_data\pop_mfre_total_6.json")
    ces4 = gpd.read_file('C:\\Users\\ariba\\Documents\\ArcGIS\\Projects\\Oakland EV Mapping ABB\\Test Data\\CES4 Final Shapefile.shp')
    city_lims = gpd.read_file('C:\\Users\\ariba\\Downloads\\GIS Data\\City_Boundaries.shp')
    sf_lim = city_lims.loc[city_lims.CITY=='San Francisco']
    oak_lim = city_lims.loc[city_lims.CITY=='Oakland']

    #pop_mfre['centroid'] = pop_mfre.geometry.centroid #Create a centroid point column
    #pop_mfre.set_geometry('centroid', inplace=True)

    df_sf = gpd.clip(pop_mfre, sf_lim.to_crs(pop_mfre.crs))
    df_oak = gpd.clip(pop_mfre, oak_lim.to_crs(pop_mfre.crs))
    # NEVI
    nevi = gpd.read_file("C:\\Users\\ariba\\Documents\\ArcGIS\\Projects\\Oakland EV Mapping ABB\\Test Data\\Electric_Fuel_Corridor_Groups_(Updated_December_2023).shp")
    nevi = nevi.loc[nevi.Corridor_G!='Ineligible for Funding']
    nevi = nevi.buffer(1609)
    nevi_sf = gpd.clip(nevi, sf_lim.to_crs(nevi.crs))
    nevi_sf = gpd.GeoDataFrame(geometry=nevi_sf)
    nevi_oak = gpd.clip(nevi, oak_lim.to_crs(nevi.crs))
    nevi_oak = gpd.GeoDataFrame(geometry=nevi_oak)
    DATA_PATH = "C:\\Users\\ariba\\Documents\\ArcGIS\\Projects\\SF Map\\data"
    # PGE
    pge_path = "{}\\ICADisplay.gdb\\ICADisplay.gdb".format(DATA_PATH)
    layername = 'LineDetail'
    pge = gpd.read_file(pge_path, driver='fileGDB', layer=layername)

    pge_sf = gpd.clip(pge, sf_lim.to_crs(pge.crs))
    pge_oak = gpd.clip(pge, oak_lim.to_crs(pge.crs))
    #pge = pge.loc[pge['LoadCapacity_kW']>=600].buffer(60.96) #60.96 m = 200 ft
    #pgeu = pge.unary_union
    #pgebuf = gpd.GeoDataFrame(geometry=[pgeu], crs=pge.crs)
    
    # IRS 30C
    irs30c = gpd.read_file("C:\\Users\\ariba\\Documents\\ArcGIS\\Projects\\Oakland EV Mapping ABB\\Test Data\\30c-all-tracts.shp")
    irs30c_sf = gpd.clip(irs30c, sf_lim.to_crs(irs30c.crs))
    irs30c_oak = gpd.clip(irs30c, oak_lim.to_crs(irs30c.crs))

    def format_irs30c(irs30c):
        irs30c = irs30c.loc[(irs30c.nonurb==1) | (irs30c.nmtc==1)]
        to_drop = [c for c in irs30c.columns if c!='geometry']
        irs30c.drop(columns=to_drop, inplace=True, errors='ignore')
        return irs30c

    irs30c_sf = format_irs30c(irs30c_sf)
    irs30c_oak = format_irs30c(irs30c_oak)
    # EXISTING EV REG
    vehicle_count = pd.read_csv('{}\\vehicle-fuel-type-count-by-zip-code-2022.csv'.format(DATA_PATH), usecols=['Zip Code', 'Fuel', 'Duty', 'Vehicles'])
    #lev = gpd.read_file("C:\\Users\\ariba\\OneDrive\\Documents\\ArcGIS\\Projects\\Oakland EV Mapping ABB\\Test Data\\LEV Vehicle per capita.shp")
    #lev['lev_pc'] = lev['sum_Number']/lev['population']

    lev_count = vehicle_count.loc[(vehicle_count['Fuel']=='Battery Electric') & (vehicle_count['Duty']=='Light')].groupby(['Zip Code']).sum()
    lev_count.drop(columns=['Fuel', 'Duty'], inplace=True, errors='ignore')
    lev_count = lev_count.reset_index()
    lev_count['Zip Code'] = [str(e) for e in lev_count['Zip Code']]

    zipcodes_sf = gpd.read_file('{}\\California_Zip_Codes.geojson'.format(DATA_PATH))
    zipcodes_sf.rename(columns={'ZIP_CODE': 'Zip Code'}, inplace=True)
    lev_sf = zipcodes_sf.merge(lev_count, how='left', on='Zip Code')
    lev_sf['lev_pc'] = lev_sf['Vehicles']/lev_sf['POPULATION']
    lev_sf['lev_10000'] = lev_sf.lev_pc*10000

    zipcodes_oak = gpd.read_file('{}\\California_Zip_Codes.shp'.format(DATA_PATH))
    zipcodes_oak.rename(columns={'ZIP_CODE': 'Zip Code'}, inplace=True)
    lev_oak = zipcodes_oak.merge(lev_count, how='left', on='Zip Code')
    lev_oak['lev_pc'] = lev_oak['Vehicles']/lev_oak['POPULATION']
    lev_oak['lev_10000'] = lev_oak.lev_pc*10000
    sf_ej = gpd.read_file('{}\\San Francisco Environmental Justice Communities Map_20240307.geojson'.format(DATA_PATH))
    sf_ej.score = sf_ej.score.astype(int)
    sf_ej.loc[sf_ej.score==999, 'score'] = 0
    def join_binary(left, right, name):
        right = gpd.GeoDataFrame(right)
        left = gpd.sjoin(left, right.to_crs(left.crs), how="left")
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
        left.loc[left['index_right'].isna(), column] = 0
        left.rename(columns={column: name}, inplace=True)
        left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
        return left
    def join_nearest(left, right, columns):
        to_drop = [c for c in right.columns if c not in columns and c!='geometry']
        right2 = right.drop(columns=to_drop, errors='ignore')
        left = gpd.sjoin_nearest(left, right2.to_crs(left.crs), how="left")
        left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
        return left
    def join_pge(left, pge):
        to_drop = [c for c in pge.columns if c!='LoadCapacity_kW' and c!='geometry']
        right2 = pge.drop(columns=to_drop, errors='ignore')
        left.set_geometry('geometry', inplace=True)
        left = left.sjoin(right2.to_crs(left.crs), how='left')
        left.set_geometry('centroid', inplace=True)
        left = left.sort_values('LoadCapacity_kW', ascending=False).drop_duplicates('geometry').sort_index()
        left['LoadCapacity_kW'].fillna(0, inplace=True)
        left.rename(columns={"LoadCapacity_kW": 'pge'}, inplace=True)
        left.drop(columns=['index_left', 'index_right'], inplace=True, errors='ignore')
        return left
    df_sf_r['centroid'] = df_sf_r.geometry.centroid #Create a centroid point column
    df_sf_r.set_geometry('centroid', inplace=True)
    sf_pop = join_nearest(df_sf_r, sf_ej, ['score'])
    sf_pop.rename(columns={'score': 'sf_ej_score'}, inplace=True)
    sf_pop = join_nearest(sf_pop, ces4, ['CIscoreP'])
    sf_pop = join_binary(sf_pop, nevi_sf, 'nevi')
    sf_pop = join_pge(sf_pop, pge_sf)
    sf_pop = join_nearest(sf_pop, zoning_sf, ['zoning_residential_multi_family', 'zoning_commercial', 'zoning_mixed'])
    sf_pop = join_binary(sf_pop, irs30c_sf, 'irs30c')
    sf_pop = join_numeric(sf_pop, lev_sf, 'lev_10000', 'lev_10000')
    sf_pop.set_geometry('geometry', inplace=True)
    to_drop = ['centroid']
    sf_pop.drop(columns=to_drop, inplace=True, errors='ignore')
    df_oak_r['centroid'] = df_oak_r.geometry.centroid #Create a centroid point column
    df_oak_r.set_geometry('centroid', inplace=True)
    oak_pop = join_nearest(df_oak_r, ces4, ['CIscoreP'])
    oak_pop = join_binary(oak_pop, nevi_oak, 'nevi')
    oak_pop = join_pge(oak_pop, pge_oak)
    oak_pop = join_nearest(oak_pop, zoning_oak, ['zoning_residential_multi_family', 'zoning_commercial', 'zoning_mixed'])
    oak_pop = join_binary(oak_pop, irs30c_oak, 'irs30c')
    oak_pop = join_numeric(oak_pop, lev_oak, 'lev_10000', 'lev_10000')
    oak_pop.set_geometry('geometry', inplace=True)
    to_drop = ['centroid']
    oak_pop.drop(columns=to_drop, inplace=True, errors='ignore')
    #sf_pop.to_file("{}\\sf_pop_pixels4.shp".format(DATA_PATH), driver='ESRI Shapefile')
    sf_pop['Renters'] = sf_pop['pop']*sf_pop['% R']/100
    sf_pop['Multi-Family Housing Residents'] = sf_pop['pop']*sf_pop['% MF']/100

    oak_pop['Renters'] = oak_pop['pop']*oak_pop['% R']/100
    oak_pop['Multi-Family Housing Residents'] = oak_pop['pop']*oak_pop['% MF']/100
    to_drop = ['% SF_OO', '% R', '% MF', 'sfoo']
    sf_pop.drop(columns=to_drop, inplace=True, errors='ignore')
    oak_pop.drop(columns=to_drop, inplace=True, errors='ignore')
    sf_pop.to_file("{}\\sf_pop_pixels_4_4.json".format(DATA_PATH), driver='GeoJSON')
    oak_pop.to_file("{}\\oak_pop_pixels_4_4.json".format(DATA_PATH), driver='GeoJSON')
    sf_pop.columns


    sf_pop = gpd.read_file("{}\\sf_pop_pixels_4_4.json".format(DATA_PATH))
    oak_pop = gpd.read_file("{}\\oak_pop_pixels_4_4.json".format(DATA_PATH))

    sf_pop['Renters'] = sf_pop['Renters']*100
    sf_pop['Multi-Family Housing Residents'] = sf_pop['Multi-Family Housing Residents']*100

    oak_pop['Renters'] = oak_pop['Renters']*100
    oak_pop['Multi-Family Housing Residents'] = oak_pop['Multi-Family Housing Residents']*100
    sf_pop.to_file("{}\\sf_priority.json".format(DATA_PATH), driver='GeoJSON')
    oak_pop.to_file("{}\\oak_priority.json".format(DATA_PATH), driver='GeoJSON')

    sf_pop.to_file("{}\\sf_feasibility.json".format(DATA_PATH), driver='GeoJSON')
    oak_pop.to_file("{}\\oak_feasibility.json".format(DATA_PATH), driver='GeoJSON')






    sf_pop.columns











    def complete_frags(pop, iso): #, fr):
        pop['centroid'] = pop.geometry.centroid
        pop2 = pop.set_geometry('centroid')
        pop2['sfoo'] = pop2['pop']*pop2['% SF_OO']
        pop_iso = pop2.sjoin(iso.to_crs(pop2.crs), how='left', predicate='within')
        pop_by_iso = pop_iso.groupby('index_right')['pop'].sum()
        sfoo_by_iso = pop_iso.groupby('index_right')['sfoo'].sum()

        idx_orig_pop = pop_by_iso.index
        pop_by_iso = pop_by_iso.combine_first(iso['num_chg'])
        idx_orig_sfoo = sfoo_by_iso.index
        sfoo_by_iso = sfoo_by_iso.combine_first(iso['num_chg'])

        iso['num_chg_pop1000'] = np.divide(iso['num_chg'], pop_by_iso/1000, where=pop_by_iso>=1)
        iso['num_chg_sfoo1000'] = np.divide(iso['num_chg'], (pop_by_iso-sfoo_by_iso)/1000, where=sfoo_by_iso>=1)

        iso.loc[~iso.index.isin(idx_orig_pop), 'num_chg_pop1000'] = np.nan
        iso.loc[~iso.index.isin(idx_orig_sfoo), 'num_chg_sfoo1000'] = np.nan

        # fr2 = fr.copy()
        # fr2['centroid'] = fr2.geometry.centroid
        # fr2 = fr2.set_geometry('centroid')
        # iso['geometry'] = iso.buffer(1e-14)
        pop2['chg'] = (pop2
                    .sjoin(iso, predicate='within', how='left')
                    .reset_index()
                    .groupby('index')['num_chg'].sum())
        pop2['chg_pop1000'] = (pop2
                            .sjoin(iso, predicate='within', how='left')
                            .reset_index()
                            .groupby('index')['num_chg_pop1000'].sum())
        pop2['chg_sfoo1000'] = (pop2
                            .sjoin(iso, predicate='within', how='left')
                            .reset_index()
                            .groupby('index')['num_chg_sfoo1000'].sum())
        # fr2 = fr2.loc[~fr2.geometry.is_empty]
        pop2.drop(columns=['centroid'], inplace=True)
        pop2.set_geometry('geometry', inplace=True)

        pop2.chg.fillna(0, inplace=True)
        pop2.chg_pop1000.fillna(0, inplace=True)
        pop2.chg_sfoo1000.fillna(0, inplace=True)

        return pop2
    iso_l2 = gpd.read_file(r"C:\Users\ariba\Documents\GSR\EV Equity\savio\data\isochrones\isochrones_walk_L2_10.0.json")
    iso_dcf = gpd.read_file(r"C:\Users\ariba\Documents\GSR\EV Equity\savio\data\isochrones\isochrones_drive_DCF_10.0.json")
    old_sums = ['sum_overlaps_walk_L2_5',
        'sum_overlaps_pop1000_walk_L2_5', 'sum_overlaps_sfoo1000_walk_L2_5',
        'sum_overlaps_walk_L2_10', 'sum_overlaps_pop1000_walk_L2_10',
        'sum_overlaps_sfoo1000_walk_L2_10', 'sum_overlaps_walk_L2_15',
        'sum_overlaps_pop1000_walk_L2_15', 'sum_overlaps_sfoo1000_walk_L2_15',
        'sum_overlaps_drive_DCF_5', 'sum_overlaps_pop1000_drive_DCF_5',
        'sum_overlaps_sfoo1000_drive_DCF_5', 'sum_overlaps_drive_DCF_10',
        'sum_overlaps_pop1000_drive_DCF_10',
        'sum_overlaps_sfoo1000_drive_DCF_10', 'sum_overlaps_drive_DCF_15',
        'sum_overlaps_pop1000_drive_DCF_15',
        'sum_overlaps_sfoo1000_drive_DCF_15']
    def redo_times(df, iso_w, iso_d, old_sums):
        new_df = complete_frags(df, iso_w)
        suffix = 'walk'
        new_df.rename(columns={'chg': f'chg_{suffix}',
                            'chg_pop1000': f'chg_pop1000_{suffix}',
                            'chg_sfoo1000': f'chg_sfoo1000_{suffix}'}, inplace=True)
        new_df = complete_frags(new_df, iso_d)
        suffix = 'drive'
        new_df.rename(columns={'chg': f'chg_{suffix}',
                            'chg_pop1000': f'chg_pop1000_{suffix}',
                            'chg_sfoo1000': f'chg_sfoo1000_{suffix}'}, inplace=True)
        new_df.drop(columns=old_sums, inplace=True)
        return new_df
    df_sf_r = redo_times(df_sf, iso_l2, iso_dcf, old_sums)
    df_oak_r = redo_times(df_oak, iso_l2, iso_dcf, old_sums)
    sf_dcf.plot(column='sum_overlaps_drive_DCF_10')
    sf_dcf.plot(column='chg_sfoo1000')


    df_oak.loc[df_oak.chg_drive_DCF_5<=0].plot(column='chg_drive_DCF_5')
