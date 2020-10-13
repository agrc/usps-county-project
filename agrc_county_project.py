from pathlib import Path

import arcpy
import os
import csv
from time import strftime

countyFipsDomain = {
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

# fixedTxtFields = [
#     'CCONTACT NAME',
#     'COMPANY NAME',
#     'ADDRESS LINE',
#     'CITY',
#     'STATE',
#     'ZIP5',
#     'ZIP4',
#     'CONGRESSIONAL CODE',
#     'COUNTY CODE',
#     'FILLER',
#     'Key',
#     'LATITUDE',
#     'LONGITUDE',
# ]

# fixedTxtFieldLengths = [
#     42,
#     66,
#     66,
#     28,
#     2,
#     5,
#     4,
#     4,
#     5,
#     19,
#     50,
#     15,
#     15,
# ]

# def createFixedLengthText(row):
#     fieldLengths = fixedTxtFieldLengths
#     try:
#         fields = list(row)
#         for i in range(11):
#             fields[i] = fields[i][:fieldLengths[i]] + (fieldLengths[i] - len(fields[i])) * ' '
#             if len(fields[i]) != fieldLengths[i]:
#                 print(f'Field length error: {fields[i]}')
#         for i in (11, 12):
#             fields[i] = (fieldLengths[i] - len(fields[i])) * ' ' + fields[i][:fieldLengths[i]]
#             if len(fields[i]) != fieldLengths[i]:
#                 print(f'Field length error: {fields[i]}')
#     except:
#         print(row)

#     return ''.join(fields)


def createCsvRow(row):
    try:
        fields = list(row)
        fields[2] = fields[2].upper()
        fields[3] = fields[3].upper()
        fields[6] = ''
        fields[-1] = fields[-1][:15]
        fields[-2] = fields[-2][:15]
    except:
        print(row)

    return ','.join(fields)


# def getFieldI(fieldName):
#     return addrFields.index(fieldName)

if __name__ == '__main__':

    unique_run_id = strftime("%Y%m%d_%H%M%S")
    print(unique_run_id)

    county_ids = ['49055']

    schema_template = r'c:\gis\git\usps-county-project\County_Project_Submission_Template.gdb\CP_Submit_template'
    sgid_connection = r'c:\gis\projects\fastdata\internal.agrc.utah.gov.sde'

    #: Source data
    addressPointsWorkspace = r'c:\gis\projects\fastdata\USPSAddress\Address.gdb'
    source_fc_name = 'WayneCo20200923'
    source_fc_path = Path(addressPointsWorkspace, source_fc_name)

    #: Set up output locations
    print('Setting up output spaces...')
    output_folder = Path(r'c:\gis\projects\fastdata\USPSAddress\out2')
    output_gdb_name = 'outputs.gdb'
    output_gdb_path = Path(output_folder, output_gdb_name)

    output_folder.mkdir(parents=True, exist_ok=True)

    if not arcpy.Exists(str(output_gdb_path)):
        arcpy.CreateFileGDB_management(output_folder, output_gdb_name)

    #: Pre-CSV output feature class
    output_fc_path = Path(output_gdb_path, f'countyProject_{unique_run_id}')
    arcpy.CreateFeatureclass_management(
        str(output_gdb_path), f'countyProject_{unique_run_id}', template=schema_template
    )

    #: District identity datasets
    congressional_districts_fc_path = Path(sgid_connection, 'SGID.POLITICAL.USCongressDistricts2012')
    identify_result_fc_path = Path(output_folder, output_gdb_name, 'addressPointsProject' + unique_run_id)

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
    ]

    counties = {
        'KANE': [],
        'MILLARD': [],
        'SANPETE': [],
        'CARBON': [],
        'UTAH': [],
        'CACHE': [],
        'SUMMIT': [],
        'WASHINGTON': [],
        'GRAND': [],
        'UINTAH': [],
        'TOOELE': [],
        'SEVIER': [],
        'GARFIELD': [],
        'BOX ELDER': [],
        'IRON': [],
        'WEBER': [],
        'EMERY': [],
        'RICH': [],
        'WASATCH': [],
        'BEAVER': [],
        'DAGGETT': [],
        'DAVIS': [],
        'WAYNE': [],
        'PIUTE': [],
        'MORGAN': [],
        'SALT LAKE': [],
        'DUCHESNE': [],
        'JUAB': [],
        'SAN JUAN': [],
    }

    # Fields to be converted to USPS county project format.
    # 'CountyID', 'FullAdd', 'City', 'ZipCode' must exist in the addressPoints table.
    source_fields = ['OID@', 'CountyID', 'FullAdd', 'City', 'ZipCode', 'DISTRICT', 'SHAPE@Y', 'SHAPE@X']

    # Set with county_ids list
    county_selection_where = None
    if len(county_ids) > 0:
        county_ids_string = ','.join(county_ids)
        county_selection_where = f"CountyID IN ('{county_ids_string}')"
    address_layer = 'addrpoints_' + unique_run_id
    arcpy.MakeFeatureLayer_management(str(source_fc_path), address_layer, county_selection_where)

    #: Get the congressional district for each address point
    print('Running Congressional District identify...')
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
    arcpy.env.geographicTransformations = 'NAD_1983_To_WGS_1984_5'
    arcpy.Identity_analysis(address_layer, str(congressional_districts_fc_path), str(identify_result_fc_path))

    #: Copy address points w/district info to countyProject feature class
    print('Copying data to output feature class and list...')
    with arcpy.da.SearchCursor(str(identify_result_fc_path), source_fields) as source_cursor,\
         arcpy.da.InsertCursor(str(output_fc_path), output_fields) as output_cursor:

        for source_address_row in source_cursor:
            object_id, county_id, full_address, city, zip_code, district, shape_y, shape_x = source_address_row
            output_address_row = []
            # County Project NAME
            output_address_row.append(countyFipsDomain[int(county_id)])
            # County Project COMPANYNAME
            output_address_row.append('AGRC')
            # County Project ADDRESSLINE
            output_address_row.append(full_address)
            # County Project CITY
            output_address_row.append(city)
            # County Project STATE
            output_address_row.append('UT')
            # County Project ZIP5
            output_address_row.append(zip_code)
            # County Project ZIP4
            output_address_row.append(0)
            # County Project CONGRESSIONALCODE
            output_address_row.append(f'UT0{district}')
            # County Project COUNTYCODE
            output_address_row.append(f'UT{county_id[-3:]}')
            # County Project FILLER
            output_address_row.append('')
            # County Project KEY
            output_address_row.append(object_id)
            # County Project LATITUDE
            output_address_row.append(shape_y)
            # County Project LONGITUDE
            output_address_row.append(shape_x)
            # CountyProject row insert
            output_cursor.insertRow(output_address_row)
            # County project rows
            counties[output_address_row[0]].append(output_address_row)

    headerString = ','.join(output_fields)
    # List will be created for each id in county_ids
    # Output file should be a csv
    print('Writing csv...')
    for county in counties:
        output_csv_path = Path(output_folder, f'{county}_{unique_run_id}.csv')
        row_list = counties[county]
        if len(row_list) > 0:
            with open(output_csv_path, 'w') as output_file:
                output_file.write(headerString + '\n')
                for row in row_list:
                    try:
                        rowString = createCsvRow([str(x) for x in row])
                        output_file.write(rowString + '\n')
                    except:
                        print(row)

                output_file.write('\n')

    print('! - complete - !')
