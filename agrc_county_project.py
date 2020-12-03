from collections import defaultdict
import csv
from pathlib import Path
from time import strftime

import arcpy

if __name__ == '__main__':

    unique_run_id = strftime("%Y%m%d_%H%M%S")
    print(unique_run_id)

    #: Source data
    county_ids = ['49005']
    source_gdb = r'c:\gis\projects\fastdata\USPSAddress\Address.gdb'
    address_source_fc_name = 'CacheCo20201202'
    address_source_fc_path = Path(source_gdb, address_source_fc_name)

    #: Static configuration data
    schema_template = r'c:\gis\git\usps-county-project\County_Project_Submission_Template.gdb\CP_Submit_template'
    sgid_connection = r'c:\gis\projects\fastdata\opensgid.agrc.utah.gov.sde'

    # Fields to be converted to USPS county project format.
    # 'CountyID', 'FullAdd', 'City', 'ZipCode', 'addsystem' must exist in the addressPoints table.
    source_fields = [
        'OID@', 'CountyID', 'FullAdd', 'City', 'ZipCode', 'DISTRICT', 'name', 'addsystem', 'SHAPE@Y', 'SHAPE@X',
        'SHAPE@'
    ]

    output_fields = [
        'NAME',
        'COMPANYNAME',
        'ADDRESSLINE',
        'CITY',
        'STATE',
        'ZIP5',
        'ZIP4',
        'CONGRESSIONALCODE',
        'COUNTYCODE',
        'FILLER',
        'KEY',
        'LATITUDE',
        'LONGITUDE',
        'SHAPE@',
    ]

    fips_to_county = {
        49025: 'KANE',
        49027: 'MILLARD',
        49039: 'SANPETE',
        49007: 'CARBON',
        49049: 'UTAH',
        49005: 'CACHE',
        49043: 'SUMMIT',
        49053: 'WASHINGTON',
        49019: 'GRAND',
        49047: 'UINTAH',
        49045: 'TOOELE',
        49041: 'SEVIER',
        49017: 'GARFIELD',
        49003: 'BOX ELDER',
        49021: 'IRON',
        49057: 'WEBER',
        49015: 'EMERY',
        49033: 'RICH',
        49051: 'WASATCH',
        49001: 'BEAVER',
        49009: 'DAGGETT',
        49011: 'DAVIS',
        49055: 'WAYNE',
        49031: 'PIUTE',
        49029: 'MORGAN',
        49035: 'SALT LAKE',
        49013: 'DUCHESNE',
        49023: 'JUAB',
        49037: 'SAN JUAN',
    }

    #: Set up output locations
    print('Setting up output spaces...')
    output_folder = Path(r'c:\gis\projects\fastdata\USPSAddress\out2')
    output_gdb_name = 'outputs.gdb'
    output_gdb_path = Path(output_folder, output_gdb_name)

    output_folder.mkdir(parents=True, exist_ok=True)

    if not arcpy.Exists(str(output_gdb_path)):
        arcpy.CreateFileGDB_management(output_folder, output_gdb_name)

    #: USPS-formatted data as a feature class
    #: SHAPE@ geometery not written to CSV
    output_fc_path = Path(output_gdb_path, f'CountyProject_{unique_run_id}')
    arcpy.CreateFeatureclass_management(
        str(output_gdb_path),
        f'CountyProject_{unique_run_id}',
        geometry_type='POINT',
        template=schema_template,
        spatial_reference=str(address_source_fc_path)
    )

    #: District identity datasets
    congressional_districts_fc_path = Path(sgid_connection, 'opensgid.political.us_congress_districts')
    identify_result_fc_path = Path(output_folder, output_gdb_name, f'Addresses_Districts_{unique_run_id}')

    #: City name spatial join datasets
    #: TODO: Should we do a definition query on the nearest points to ensure it gets a town in the same county? Do zip codes follow County boundaries?
    city_names_fc_path = Path(sgid_connection, 'opensgid.location.city_and_town_locations')
    spatial_join_fc_path = Path(output_folder, output_gdb_name, f'City_Name_Spatial_Join_{unique_run_id}')

    #: Make layer of only our specified counties
    county_selection_where = None
    if county_ids:
        county_ids_string = ','.join(county_ids)
        county_selection_where = f"CountyID IN ('{county_ids_string}')"
    address_layer = f'addrpoints_{unique_run_id}'
    arcpy.MakeFeatureLayer_management(str(address_source_fc_path), address_layer, county_selection_where)

    #: Get the congressional district for each address point
    print('Running Congressional District identify...')
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
    arcpy.env.geographicTransformations = 'NAD_1983_To_WGS_1984_5'
    arcpy.Identity_analysis(address_layer, str(congressional_districts_fc_path), str(identify_result_fc_path))

    #: Get the nearest city point to be used as city name for unicorporated areas
    print('Running nearest city spatial join...')
    arcpy.SpatialJoin_analysis(
        str(identify_result_fc_path),
        str(city_names_fc_path),
        str(spatial_join_fc_path),
        match_option='CLOSEST',
        search_radius='50 Miles',
        distance_field_name='MatchDistance'
    )

    #: Copy address points w/district info to dict of counties containing list of dicts of addresses
    #: {county: [{address, city, etc}, ...], ...}
    print('Loading and formatting source data...')
    counties = defaultdict(list)  #: defaultdict adds new key with an empty list if key is not yet present

    #: Get a unique list of address systems in the dataset
    #: Using a python set instead of list or dict
    address_systems = set()
    with arcpy.da.SearchCursor(str(spatial_join_fc_path), ['addsystem']) as addrsys_cursor:
        address_systems = {row[0].upper() for row in addrsys_cursor}

    with arcpy.da.SearchCursor(str(spatial_join_fc_path), source_fields) as source_cursor:
        for row in source_cursor:
            object_id, county_id, full_address, city, zip_code, district, nearest_city, address_system, shape_y, shape_x, geometry = row

            formatted_address = dict.fromkeys(output_fields)
            county_name = fips_to_county[int(county_id)]

            #: Use the nearest_city name unless there is a name provided in the address point data itself or it is
            #: in the list of address systems (indicating it could have grabbed a name that was closer geographically
            #: than topologically)
            proper_city = nearest_city.upper()
            if city.upper():
                proper_city = city.upper()
            elif nearest_city.upper() in address_systems:
                proper_city = address_system

            formatted_address['NAME'] = county_name
            formatted_address['COMPANYNAME'] = 'AGRC'
            formatted_address['ADDRESSLINE'] = full_address.upper()
            formatted_address['CITY'] = proper_city
            formatted_address['STATE'] = 'UT'
            formatted_address['ZIP5'] = zip_code
            formatted_address['ZIP4'] = None
            formatted_address['CONGRESSIONALCODE'] = f'UT0{district}'
            formatted_address['COUNTYCODE'] = f'UT{county_id[-3:]}'
            formatted_address['FILLER'] = ''
            formatted_address['KEY'] = object_id
            formatted_address['LATITUDE'] = str(shape_y)[:15]
            formatted_address['LONGITUDE'] = str(shape_x)[:15]
            formatted_address['SHAPE@'] = geometry

            counties[county_name].append(formatted_address)

    print('Writing to feature class...')
    with arcpy.da.InsertCursor(str(output_fc_path), output_fields) as output_cursor:
        #: Loop through all counties
        for county, addresses in counties.items():

            #: Loop through all records for that county
            for record in addresses:
                output_row = []

                #: Build row using output_fields to ensure field order (insertion order not guaranteed in python < 3.7)
                for field_name in output_fields:
                    output_row.append(record[field_name])

                output_cursor.insertRow(output_row)

    #: Create output csv for USPS for every county in counties
    print('Writing to csv...')
    output_fields.remove('SHAPE@')  #: Don't include geometry in CSV
    for county, addresses in counties.items():
        output_csv_path = Path(output_folder, f'{county}_{unique_run_id}.csv')
        if addresses:
            with open(output_csv_path, 'w', newline='\n') as output_file:
                csv_writer = csv.DictWriter(output_file, output_fields, extrasaction='ignore')
                csv_writer.writeheader()
                csv_writer.writerows(addresses)

    print('! - complete - !')
