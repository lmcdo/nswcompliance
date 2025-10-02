please reoutput integrating the below api calls to get the existing planning data for an user input address:

clicking on the map and address input search gets planning data for the selected property via 3 it seems api calls. is this correct? if so please provide the api requests code that 

@https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=85%20Thompson%20St%2C%20Drummoyne%20NSW%202047%2C%20Australia&noOfRecords=1
 [
 {
 "address": "85 THOMPSON STREET DRUMMOYNE 2047",
 "propId": 1909711,
 "GURASID": 2458866
 }
]

@ https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=1909711&layers=epi
 [
 {
 "id": "11",
 "layerName": "Floor Space Ratio Map",
 "results": [
 {
 "Amendment": "Map Amendment No 2",
 "Commenced Date": "2-12-2022",
 "Currency Date": "25-7-2025",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "Floor Space Ratio": "0.5",
 "Legislative Clause": "Clause 4.4",
 "LGA Name": "CANADA BAY",
 "Published Date": "2-12-2022",
 "title": "0.5:1",
 "legislationUrl": " https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 },
 {
 "id": "14",
 "layerName": "Height of Buildings Map",
 "results": [
 {
 "Amendment": "Map Amendment No 2",
 "Commenced Date": "2-12-2022",
 "Currency Date": "27-11-2024",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "Legislative Clause": "Clause 4.3",
 "LGA Name": "CANADA BAY",
 "Maximum Building Height": "8.5",
 "Published Date": "2-12-2022",
 "title": "8.5 m",
 "Units": "m",
 "legislationUrl": " https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 },
 {
 "id": "19",
 "layerName": "Land Zoning Map",
 "results": [
 {
 "Amendment": "Map Amendment No 3",
 "Commenced Date": "26-4-2023",
 "Currency Date": "27-11-2024",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "Land Use": "Low Density Residential",
 "LGA Name": "CANADA BAY",
 "Published Date": "21-4-2023",
 "title": "R2: Low Density Residential",
 "Zone": "R2",
 "legislationUrl": " https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 },
 {
 "id": "8",
 "layerName": "Land Application Map",
 "results": [
 {
 "Amendment": "Map Amendment No 2",
 "Commenced Date": "2-12-2022",
 "Currency Date": "2-12-2022",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "Legislative Clause": "Clause 1.3",
 "LGA Name": "CANADA BAY",
 "Published Date": "2-12-2022",
 "title": "Canada Bay Local Environmental Plan 2013",
 "Type": "Included",
 "legislationUrl": " https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 },
 {
 "id": "16",
 "layerName": "Heritage Map",
 "results": [
 {
 "Amendment": "Amendment No 29",
 "Commenced Date": "12-7-2024",
 "Currency Date": "27-11-2024",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "Heritage Type": "Conservation Area - General",
 "Item Name": "Bourketown",
 "Item Number": "CA",
 "Legislative Clause": "Clause 5.10",
 "LGA Name": "CANADA BAY",
 "Published Date": "12-7-2024",
 "Significance": "Local",
 "title": "Bourketown Significance: Local",
 "legislationUrl": " https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 },
 {
 "id": "6",
 "layerName": "Local Aboriginal Land Council",
 "results": [
 {
 "Local Council Name": "METROPOLITAN",
 "Regional Council Name": "SYDNEY NEWCASTLE",
 "title": "METROPOLITAN"
 }
 ]
 },
 {
 "id": "22",
 "layerName": "Lot Size Map",
 "results": [
 {
 "Amendment": "Map Amendment No 2",
 "Commenced Date": "2-12-2022",
 "Currency Date": "27-11-2024",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "Legislative Clause": "Clause 4.1",
 "LGA Name": "CANADA BAY",
 "Lot Size": "450",
 "Published Date": "2-12-2022",
 "title": "450 m²",
 "Units": "m²",
 "legislationUrl": " https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 },
 {
 "id": "1",
 "layerName": "Greater Sydney Tree Canopy Cover 2022",
 "results": [
 {
 "Canopy %": "11.11",
 "title": "Canopy %"
 }
 ]
 },
 {
 "id": "149",
 "layerName": "Special Provisions",
 "results": [
 {
 "Class": "5",
 "Commenced Date": "1-10-2023",
 "Currency Date": "1-10-2023",
 "EPI Name": "State Environmental Planning Policy (Sustainable Buildings) 2022",
 "EPI Type": "SEPP",
 "Label": "CANADA BAY",
 "Map Type": "BAL",
 "Published Date": "29-8-2022",
 "title": "SEPP (Sustainable Buildings) 2022 Climate Zones for BASIX Alterations Map",
 "Type": "Climate Zones"
 },
 {
 "Class": "40%",
 "Commenced Date": "1-10-2023",
 "Currency Date": "1-10-2023",
 "EPI Name": "State Environmental Planning Policy (Sustainable Buildings) 2022",
 "EPI Type": "SEPP",
 "Label": "2047",
 "Map Type": "WAT",
 "Published Date": "29-8-2022",
 "title": "SEPP (Sustainable Buildings) 2022 Water Use Map",
 "Type": "Minimum Water Use Standard (%)"
 },
 {
 "Amendment": "State Environmental Planning Policy (Transport and Infrastructure) Amendment (Thermal Energy from Waste) 2022",
 "Class": "Greater Sydney",
 "Commenced Date": "16-12-2022",
 "Currency Date": "16-12-2022",
 "EPI Name": "State Environmental Planning Policy (Transport and Infrastructure) 2021",
 "EPI Type": "SEPP",
 "Map Type": "TEW",
 "Published Date": "16-12-2022",
 "title": "Thermal Energy from Waste Prohibition Map - Greater Sydney",
 "Type": "Greater Sydney"
 },
 {
 "Class": "56",
 "Commenced Date": "1-10-2023",
 "Currency Date": "1-10-2023",
 "EPI Name": "State Environmental Planning Policy (Sustainable Buildings) 2022",
 "EPI Type": "SEPP",
 "Label": "2047",
 "Map Type": "CLM",
 "Published Date": "29-8-2022",
 "title": "SEPP (Sustainable Buildings) 2022 Climate Zones for BASIX Buildings Map",
 "Type": "Climate Zones"
 }
 ]
 },
 {
 "id": "0",
 "layerName": "Greater Sydney Tree Canopy Cover 2019",
 "results": [
 {
 "Canopy %": "10.09",
 "title": "Canopy %"
 }
 ]
 },
 {
 "id": "310",
 "layerName": "Regional Plan Boundary",
 "results": [
 {
 "Regional Plan Website": "&lt;a href=\" https://bit.ly/3oaehef \"&gt;Greater Sydney&lt;/a&gt;",
 "title": "Greater Sydney"
 }
 ]
 },
 {
 "id": "234",
 "layerName": "Acid Sulfate Soils Map",
 "results": [
 {
 "Amendment": "Map Amendment No 2",
 "Class": "Class 5",
 "Commenced Date": "2-12-2022",
 "Currency Date": "2-12-2022",
 "EPI Name": "Canada Bay Local Environmental Plan 2013",
 "EPI Type": "LEP",
 "LGA Name": "CANADA BAY",
 "Published Date": "2-12-2022",
 "title": "Class 5",
 "legislationUrl": "https://www.legislation.nsw.gov.au/#/view/EPI/2013/389"
 }
 ]
 }
]
@ https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query?where=propid=1909711&outFields=propid,address,val1_bd,val1_lv,prop_area,zone_desc,urbanity&f=json
 {"displayFieldName":"urbanity","fieldAliases":{"propid":"propid","address":"address","val1_bd":"val1_bd","val1_lv":"val1_lv","prop_area":"prop_area","zone_desc":"zone_desc","urbanity":"urbanity"},"geometryType":"esriGeometryPoint","spatialReference":{"wkid":102100,"latestWkid":3857},"fields":[{"name":"propid","type":"esriFieldTypeInteger","alias":"propid"},{"name":"address","type":"esriFieldTypeString","alias":"address","length":255},{"name":"val1_bd","type":"esriFieldTypeString","alias":"val1_bd","length":20},{"name":"val1_lv","type":"esriFieldTypeString","alias":"val1_lv","length":20},{"name":"prop_area","type":"esriFieldTypeString","alias":"prop_area","length":30},{"name":"zone_desc","type":"esriFieldTypeString","alias":"zone_desc","length":255},{"name":"urbanity","type":"esriFieldTypeString","alias":"urbanity","length":2}],"features":[{"attributes":{"propid":1909711,"address":"85 THOMPSON ST, DRUMMOYNE NSW 2047 ","val1_bd":"1 July 2024","val1_lv":" $1,870,000","prop_area":"271.9 square metres","zone_desc":"R2 - Low Density Residential","urbanity":"U"},"geometry":{"x":16826040.234499998,"y":-4009356.995000001}}]} 