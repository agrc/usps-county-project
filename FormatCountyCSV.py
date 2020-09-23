import csv
if __name__ == '__main__':
    countyFile = r'C:\GisWork\UspsCountyProject\CountyProjectOutputFile.txt'
    outputUspsFile = r'C:\GisWork\UspsCountyProject\CountyProjectOutputFull.csv'
    outputDaggetFile = r'C:\GisWork\UspsCountyProject\Counties\YSN1130.txt'
    counties = {}
    first = True
    with open(countyFile, 'r') as addresses, \
        open(outputDaggetFile, 'wb') as outputFile:
        outputCsv = csv.writer(outputFile)
        for row in addresses:
            if first:
                first = False
                outputCsv.writerow(row.split(',')[1:])
                continue
            try:
                fields = row.split(',')[1:]
                if fields[0] == 'DAGGETT':
                    fields[6] = ''
                    fields[-1] = fields[-1][:15]
                    fields[-2] = fields[-2][:15]
                    outputCsv.writerow(fields)
            except:
                print(row)
