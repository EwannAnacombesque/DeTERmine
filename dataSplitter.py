import xml.etree.ElementTree as ET
import math

class Splitter():
    def __init__(self,source_file):
        # Define all the sections
        self.sections = ["dataObjects/CompositeFrame/frames/SiteFrame/stopPlaces",
                         "dataObjects/CompositeFrame/frames/ServiceFrame/scheduledStopPoints",
                         "dataObjects/CompositeFrame/frames/ServiceFrame/stopAssignments",
                         "dataObjects/CompositeFrame/frames/TimetableFrame/vehicleJourneys",
                         "dataObjects/CompositeFrame/frames/TimetableFrame/trainNumbers",
                         "dataObjects/CompositeFrame/frames/ServiceCalendarFrame/dayTypes",
                         "dataObjects/CompositeFrame/frames/ServiceCalendarFrame/operatingPeriods",
                         "dataObjects/CompositeFrame/frames/ServiceFrame/routeLinks"
                        ]
        
        # Use the Splitter as a Splitter
        if source_file:
            # Remove namespaces
            with open(source_file,"r+") as f:
                raw_xml = f.readlines()
                raw_xml[1] = "<PublicationDelivery>\n"
                f.seek(0)
                f.writelines(raw_xml)
                
            self.tree = ET.parse(source_file)
            self.root = self.tree.getroot()
                          
    def split(self):
        # Split each section
        for section in self.sections:
            # Get the splitted filename
            filename = "Data/"+section.split("/")[-1]+".xml"
            # Get the corresponding content
            content = self.root.find(section)
            # Write i
            with open(filename, 'wb') as f:
                f.write(str.encode("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"))
                f.write(ET.tostring(content))
              
    def cleanRouteLinks(self):
        # Useless #
        
        # Get the RouteLinks
        RouteLinksTree = ET.parse("Data/"+self.sections[7].split("/")[-1]+".xml")
        RouteLinksRoot = RouteLinksTree.getroot()
        # Only keep the non null ones
        ValidRouteLinks = RouteLinksRoot.findall(".//RouteLink[Distance!='0']")
        
        # Embed those in a huge arbitrary element
        final_element = ET.Element("CleanedRouteLinks")
        final_element.extend(ValidRouteLinks)

        # Save those routeLinks
        with open("Data/CleanedRouteLinks.xml", 'wb') as f:
            f.write(str.encode("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"))
            f.write(ET.tostring(final_element))
    
    def subdivideJourneys(self):
        # Get the journeys elements
        journeysTree = ET.parse("Data/"+self.sections[3].split("/")[-1]+".xml")
        journeysRoot = journeysTree.getroot()
        journeys = journeysRoot.findall(".//ServiceJourney")
        
        # Arbitrary chosen, must correspond to the subdivisions count in main.py
        subdivisions = 20
        
        # Get the amount of journeys to treat
        journeys_count = len(journeys)
        # Get the corresponding chunk size
        chunk_size = math.ceil(journeys_count/subdivisions)
        
        index = 0
        for i in range(0, journeys_count, chunk_size): 
            # Increment the index and get the corresponding filename
            index += 1
            filename = "Data/Subdivided/"+self.sections[3].split("/")[-1]+f"_{index}.xml"
            # Save the chunk of journeys
            with open(filename, 'wb') as f:
                f.write(str.encode("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"))
                f.write(str.encode("<vehicleJourneys>\n"))
                # Could have used extend method but subdivideJourneys() is not often
                # Called so we don't really care
                for element in journeys[i:min(i+chunk_size,journeys_count)]:
                    f.write(ET.tostring(element))
                f.write(str.encode("</vehicleJourneys>\n"))
                