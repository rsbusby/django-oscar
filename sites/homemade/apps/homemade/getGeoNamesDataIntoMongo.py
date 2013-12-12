

import homeMade as hm



geoNamesFile = "US.txt"

hm.HMGeoData.drop_collection()


f = open(geoNamesFile, 'r')

i = 0
for line in f:
    i = i+1


    lsp = line.split('\t')
    
    if i < 12:
        print(i)

    zip = lsp[1]
    lat = lsp[-3]
    long = lsp[-2]



    gd = hm.HMGeoData()
    gd.zipcode = lsp[1]
    gd.town = lsp[2]
    gd.stateFullName = lsp[3]
    gd.state = lsp[4]
    lat = lsp[-3]
    long = lsp[-2]
    gd.lat = lat
    gd.long = long
    gd.locCoords = [float(lat), float(long)]
    gd.save()
    
