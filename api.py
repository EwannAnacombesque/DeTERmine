import dataSplitter
from dataSplitter import ET
from dataSplitter import math
import threading
import pickle
import os

class StopPoint():
    def __init__(self,AbsoluteRef,ScheduledStopPointRef,StopPlaceRef,Longitude,Latitude,Name):
        self.AbsoluteRef = AbsoluteRef
        self.Location = (Longitude,Latitude)
        self.Name = Name        

        # Related to StopPointInJourneyPattern, link to StopPlaceRef : Shared between journeys
        self.ScheduledStopPointRef = ScheduledStopPointRef
        # Location information -> Postal Code, centroïd etc.
        self.StopPlaceRef = StopPlaceRef
        
        # The destinations of the stopPoint
        self.destinations = {}
 
    def __str__(self) -> str:
        return f"{self.Name} ; {self.AbsoluteRef}\n -> {self.Location[1]} ; {self.Location[0]}\n -> {self.ScheduledStopPointRef}\n -> {self.StopPlaceRef}" 
    
    def __hash__(self) -> int:
         return hash((self.AbsoluteRef, self.Location, self.Name,self.ScheduledStopPointRef,self.StopPlaceRef))

class TrainParser():
    def __init__(self):
        # Access to data
        self.getData()
        
        # State indicator
        self.state = "Initializing"

        # Dijsktra modifiers
        # For a same destination, how much the concordance of the train will
        # Favorise the train to be chosen, rather than the immediacy of the train
        # -> Local modifier, doesn't affect destination
        self.modifier = 1
        # How much a destination will be favorise in function of the concordance of the train
        # Rather than an other destination
        # -> Global modifier, affects destination
        self.postChoiceModifier = 1
        
        # Other
        self.INFINITE_DISTANCE = 9999999999999
        
        # All variables related to time
        self.monthLenghts = [0,31,28,31,30,31,30,31,31,30,31,30,31]

    def initialize(self,parseNeTEx,verbose=False) -> None:
        self.verbose = verbose
        if self.verbose: print("\n-Setting up everything-\n")
            
        # Chose between hard load and soft load
        if not parseNeTEx:
            self.updateState("Loading stop places file")
            self.loadStopPlaces()
        else:
            self.parseNeTExFile()
    
        self.placeNamesDict = self.getPlacesNames()
        self.updateState("Finished")

    def parseNeTExFile(self) -> None:
        self.updateState("Loading NeTEx file")
        splitter = dataSplitter.Splitter(self.fileName)
        self.updateState("Splitting NeTEx file")
        splitter.split()
        self.updateState("Subdividing NeTEx file")
        splitter.subdivideJourneys()
        
        # Load useful places
        self.updateState("Loading splitted files")
        self.sectionsNames = ["stopPlaces","scheduledStopPoints","stopAssignments","operatingPeriods"]
        self.trees = {}
        self.roots = {}
        self.loadSections()
        
        self.stopPlaces = {}
        self.stopPlacesDistances = {}
        # Get the stopPlaces from stopAssignments.xml and stopPlaces.xml
        self.updateState("Getting stop places")
        self.getStopPlaces()
        self.updateState("Removing empty stop places")
        self.removeEmptyStopPlaces()
        # Get the departures from vehicleJourneys_XX.xml and clean those
        self.updateState("Getting departures")
        self.getAllDepartures()
        self.updateState("Removing duplicated departures")
        self.removeDuplicatedDepartures()
        # Get the distances
        self.updateState("Getting departures distances")
        self.getDeparturesDistances()
        # Save everything
        self.updateState("Saving stop places")
        self.saveStopPlaces()

    def updateState(self,newState) -> None:
        self.state = newState
        if self.verbose: print(self.state)        

    def getData(self) -> None:
        corresponding = [file_name for file_name in os.listdir() if file_name[-3:] == "xml" and file_name[:12] == "sncf_netexfr"]
        assert len(corresponding) == 1, "Should have a single sncf_netexfr_YYYYMMDD.xml file in the directory"
        # Get file name, beginning and end dates, and reference date
        self.fileName = corresponding[0]
        self.dates = [self.fileName[17:21],self.fileName[22:26]]
        self.referenceDate = [int(self.dates[0][2:]),int(self.dates[0][:2])]

    def saveStopPlaces(self) -> None:
        # Save stop places object
        with open('Data/savedStopPlaces.data', 'wb') as f:
            pickle.dump(self.stopPlaces, f)
        # Save stop places distances object 
        with open('Data/savedStopPlacesDistances.data', 'wb') as f:
            pickle.dump(self.stopPlacesDistances, f) 
    
    def loadStopPlaces(self) -> None:
        # Verify if those files exist
        corresponding = [file_name for file_name in os.listdir("Data/") if file_name == "savedStopPlaces.data" or file_name == "savedStopPlacesDistances.data"]
        if len(corresponding) < 2:
            if self.verbose: print("Didn't find the stop places files, begin to parse NeTEx file")
            self.parseNeTExFile()
            
        # Load stop places object
        with open('Data/savedStopPlaces.data', 'rb') as f:
            self.stopPlaces = pickle.load(f)
        # Load stop places distances object
        with open('Data/savedStopPlacesDistances.data', 'rb') as f:
            self.stopPlacesDistances = pickle.load(f)

    def loadSections(self) -> None:
        # For each section create an element tree
        for section in self.sectionsNames:
            self.trees[section] = ET.parse(f"Data/{section}.xml")
            self.roots[section] = self.trees[section].getroot()
        
    def getStopPlaces(self) -> None:
        # Get each stopPlaces, in PublicationDelivery/dataObjects/SiteFrame/StopPlaces
        for StopPlace in self.roots["stopPlaces"].findall('.//StopPlace'):
            # Get the stop place identifiant
            StopPlaceRef = StopPlace.get("id")
            # Get the corresponding scheduled stop point identifiant in the stopAssignments register
            ScheduledStopPointRef = self.roots["stopAssignments"].find(f".//StopPlaceRef[@ref = '{StopPlaceRef}'].../ScheduledStopPointRef").attrib["ref"]
            # Get the number that caracterises the point
            AbsoluteRef = ScheduledStopPointRef.split(":")[-1] 
            # Get the position of the stop place
            Longitude = StopPlace.find("Centroid/Location/Longitude").text
            Latitude = StopPlace.find("Centroid/Location/Latitude").text
            # Get the name of the location
            Name = StopPlace.find("Name").text

            # Add everything to the huge dictionary
            self.stopPlaces[AbsoluteRef] = StopPoint(AbsoluteRef,ScheduledStopPointRef,StopPlaceRef,Longitude,Latitude,Name)

    def removeEmptyStopPlaces(self) -> None:
        usedStopPlaces = set()
        for stopPlaceId in self.stopPlaces.keys():
            usedStopPlaces.add(stopPlaceId)
            for departureId in self.getDeparturesIdFromPlaceId(stopPlaceId):
                usedStopPlaces.add(departureId)
        
        for stopPlaceId in self.stopPlaces.keys():
            if stopPlaceId not in usedStopPlaces:
                del self.stopPlaces[stopPlaceId]

    def getAllDepartures(self) -> None:
        subdivisions = 20
        self.departuresThreads = []

        # For each departure file create a thread and start it
        for i in range(subdivisions):
            self.departuresThreads.append(threading.Thread(target=self.getThreadedFileDepartures,group=None,daemon=True,args=(i+1,)))
            self.departuresThreads[i].start()
        # Wait for all the threads to end
        for i in range(subdivisions):
            self.departuresThreads[i].join()

    def getThreadedFileDepartures(self,index) -> None:
        # Get the corresponding file of the thread index
        tree = ET.parse(f"Data/Subdivided/vehicleJourneys_{index}.xml")
        root = tree.getroot()

        # Loop over all the ServiceJourneys
        for ServiceJourney in root.findall(".//ServiceJourney"):            
            # Get the timings of the points on the Journey
            passingTimes = ServiceJourney.findall("passingTimes/TimetabledPassingTime")
            
            # IN COMMON FOR ALL THE POINTS #
            # Get the Identifiant of the ServiceJourney
            ServiceJourneyId = ServiceJourney.attrib["id"].split(":")[-1]
            # Get the dayBits of the Service Journey
            ValidDayBits = self.getValidDayBitsFromDayTypes(ServiceJourney.find("dayTypes/DayTypeRef").attrib["ref"].split(":")[-2])
            
            # Get the identifiant and the departureTime of the first stop place
            origin = passingTimes[0].find("PointInJourneyPatternRef").attrib["ref"][37:45]
            departureTime = passingTimes[0].find("DepartureTime").text
            
            # Loop over each passing time excep the first and the last, because those are specials
            for passingTime in passingTimes[1:]:

                # Get the identifiant and the arrival time of the destination on the journey
                destinationRef = passingTime.find("PointInJourneyPatternRef").attrib["ref"][37:45]
                arrivalTime = passingTime.find("ArrivalTime").text

                # If this destination does not already exists, create the reference
                if destinationRef not in self.stopPlaces[origin].destinations:
                    self.stopPlaces[origin].destinations[destinationRef] = set()
                
                # Send the informations
                informations = (departureTime,arrivalTime,ValidDayBits,ServiceJourneyId)
                self.stopPlaces[origin].destinations[destinationRef].add(informations)
                
                # Prepare for the next stopPlace
                if passingTime == passingTimes[-1]: continue
                origin = destinationRef
                departureTime = passingTime.find("DepartureTime").text

    def removeDuplicatedDepartures(self) -> None:
        # Loop over each schedules
        for stopPlaceId in self.stopPlaces.keys():
            for departureId in self.stopPlaces[stopPlaceId].destinations.keys():
                # Get uniques trains numbers  
                filterDict = {}
                
                for schedule in self.stopPlaces[stopPlaceId].destinations[departureId]:
                    # Identifiant in common for the same trains numbers but with different dayBits
                    resumed = f"{schedule[0]} - {schedule[1]} -> {schedule[3].split('_')[0]}"
                    
                    # Get the reference
                    if resumed not in filterDict:
                        filterDict[resumed] = list(schedule)
                        continue 

                    # If the resumed already in the filter dict, fuse the validDayBits
                    filterDict[resumed][2] = self.fuseValidDayBits(filterDict[resumed][2],schedule[2])
                
                # Recreate the stopPlaces
                self.stopPlaces[stopPlaceId].destinations[departureId] = set([tuple(value) for value in filterDict.values()])

    def getDeparturesDistances(self) -> None:
        for stopPlaceId in self.stopPlaces.keys():
            self.stopPlacesDistances[stopPlaceId] = {}
            for departureId in self.stopPlaces[stopPlaceId].destinations.keys():
                self.stopPlacesDistances[stopPlaceId][departureId] = self.getDistanceBetweenPlaceIdAndDepartureId(stopPlaceId,departureId)

    def getPlacesNames(self) -> dict:
        return {stopPoint.Name:(stopPointId,len(stopPoint.destinations)) for stopPointId,stopPoint in self.stopPlaces.items()}


    # Mostly Dev Purpose #

    def getValidDayBitsFromDayTypes(self,dayTypes) -> str:
        # Returns the corresponding DayBits from a DayTypes
        return self.trees["operatingPeriods"].find(f"UicOperatingPeriod[@id='FR:OperatingPeriod:{dayTypes}']/ValidDayBits").text

    def fuseValidDayBits(self,firstDayBits,secondDayBits) -> str:
        # Proceed a bitwise OR on dayBits
        return f"{(int(firstDayBits,2)|int(secondDayBits,2)):#033b}"[2:]

    def getNameFromPlaceId(self,placeId) -> str:
        return self.stopPlaces[placeId].Name
    
    def getIdFromPlaceName(self,placeName) -> str:
        candidates = sorted([place.AbsoluteRef for place in self.stopPlaces.values() if place.Name == placeName],key=lambda placeId: self.getSchedulesCountFromPlaceId(placeId))
        if not candidates: return None 
        return candidates[-1]

    def getConfusedNames(self) -> list:
        allNames = [place.Name for place in self.stopPlaces.values()]
        return [name for name in allNames if allNames.count(name) > 1]

    def getDeparturesIdFromPlaceId(self,placeId) -> list:
        return list(self.stopPlaces[placeId].destinations.keys())

    def getDeparturesCountFromPlaceId(self,placeId) -> list:
        return len(self.stopPlaces[placeId].destinations)

    def getDeparturesNamesFromPlaceId(self,placeId) -> list:
        return [self.getNameFromPlaceId(departure) for departure in self.getDeparturesIdFromPlaceId(placeId)]

    def getDeparturesNamesFromPlaceName(self,placeName) -> list:
        placeId = self.getIdFromPlaceName(placeName)
        if not placeId: return []
        return [self.getNameFromPlaceId(departure) for departure in self.getDeparturesIdFromPlaceId(placeId)]

    def getAllSchedulesFromPlaceId(self,placeId) -> list:
        return [schedule for destinationId in self.stopPlaces[placeId].destinations.keys() for schedule in self.stopPlaces[placeId].destinations[destinationId]]

    def getSchedulesCountFromPlaceId(self,placeId) -> int:
        return len(self.getAllSchedulesFromPlaceId(placeId))

    def getSchedulesFromPlaceIdAndDepartureId(self,placeId,departureId) -> list:
        if departureId not in self.stopPlaces[placeId].destinations:
            return []
        return self.stopPlaces[placeId].destinations[departureId]

    def getSchedulesFromPlaceNameAndDepartureName(self,placeName,departureName) -> list:
        placeId,departureId = self.getIdFromPlaceName(placeName),self.getIdFromPlaceName(departureName)
        if not placeId or not departureId: return []
        
        return self.getSchedulesFromPlaceIdAndDepartureId(placeId,departureId)

    def getTrainNumberFromSchedule(self,schedule) -> str:
        return schedule[3].split("ROUTIER")[0].split("FERRE")[0][2:]

    # Computing efficient paths #

    def sortSchedulesFromPlaceIdAndDepartureId(self,placeId,departureId,dayIndex,hour,incomingTrain) -> dict:
        # Get the Schedules of a specific placeId and departureId
        Schedules = self.getSchedulesFromPlaceIdAndDepartureId(placeId,departureId)
        # Verify the Schedules aren't empty
        if not Schedules: return {}
        # Return the Schedule time offset in minutes, the Schedule end day, and the schedule itself,
        # Everything sorted by the time offset
        schedulesDict = []
        for schedule in Schedules:
            offset,day = self.getScheduleWholeTimeOffset(schedule,dayIndex,hour)
            schedulesDict.append({
                 "TimeOffset":offset,
                 "Score":offset*self.getScoreModifier(schedule,incomingTrain),
                 "ResultingDay":day,
                 "Schedule":schedule})
        return sorted(schedulesDict, key = lambda x: x["Score"])
    
    def getScoreModifier(self,schedule,incomingTrain) -> float:
        return self.modifier if self.getTrainNumberFromSchedule(schedule) == incomingTrain else 1
            
    def choseBestScheduleFromPlaceIdAndDepartureId(self,placeId,departureId,dayIndex,hour,incomingSchedule) -> dict:
        return self.sortSchedulesFromPlaceIdAndDepartureId(placeId,departureId,dayIndex,hour,incomingSchedule)[0]

    def getScheduleResultingDay(self,schedule,dayIndex,hour,byDepart) -> list:
        # Start a dayIndex minus one to get to the right index immediately after
        dayIndex -= 1

        # Loop over each dayIndex
        while dayIndex <= 60:
            dayIndex += 1

            # The day must be valid and the ArrivalTime must be superior to the hour itself
            if int(schedule[2][dayIndex%31]) and schedule[1] >= hour  and schedule[0] >= hour:
                return dayIndex
            
            # After the first iteration, we go to a next day, so the clock is reseted to 0
            hour = "00:00:00"
        
        # In case no Day has been found return a huge one, because i don't want to handle erros :)
        return 99

    def getScheduleWholeTimeOffset(self,schedule,dayIndex,hour) -> list:
        # Get the day of the Arrival
        ResultingDay = self.getScheduleResultingDay(schedule,dayIndex,hour,1)
        # Get the hours offset
        hours = int(schedule[1].split(":")[0])-int(hour.split(":")[0])
        # Get the minutes offset
        minutes = int(schedule[1].split(":")[1])-int(hour.split(":")[1])
        # Calculate the resulting time offset in minutes
        return (ResultingDay-dayIndex)*24*60 + hours*60 + minutes,ResultingDay

    def getDistanceBetweenPlaceIdAndDepartureId(self,placeId,departureId) -> int:
        # Ugly formula to get the distance between two locations,
        # It approximates the Latitude changement by computing the mean
        # I know it isn't the true distance but it does the taf fair enough
        # I use pythagoras theorem to compute the distance
        x = (float(self.stopPlaces[placeId].Location[0])-float(self.stopPlaces[departureId].Location[0]))*math.cos((float(self.stopPlaces[placeId].Location[1])*math.pi/180+float(self.stopPlaces[departureId].Location[1])*math.pi/180)*0.50)/360
        y = (float(self.stopPlaces[placeId].Location[1])-float(self.stopPlaces[departureId].Location[1]))/360
        return 40075017*math.sqrt(x**2+y**2)
    
    def processDijkstra(self,originId,destinationId,dayIndex,hour,query) -> tuple:
        # Initialize the graph, with infinite_distances
        graph = {stopPlaceId:{"distance":self.INFINITE_DISTANCE, # Theorical Distance to the origin
                                   "dayIndex":dayIndex, # Day of the point when it is achieved
                                   "ArrivalTime":hour, # Time of the arrival
                                   "incomingSchedule":("Departure","Arrival","DayBits","REF"), # The incoming Schedule data 
                                   "via":"StopPlaceID" # The identifiant of the former StopPlaceID 
                                   } for stopPlaceId in self.stopPlaces.keys()}

        # Set of nodes visited <=> distance != infinite
        visited = set()
        # Set of nodes explorated AND NOT visited <=> there is an unexploited liaison to those
        opened = set([originId])
        
        # Initialise the origin
        graph[originId]["distance"] = 0
        
        # Dijkstra Algorithm #
        while len(visited) != len(graph):
            # Get the closest place to the origin
            placeId = sorted(opened,key=lambda ID: graph[ID]["distance"])[0]
            # Get the place information
            placeData = graph[placeId]
            incomingTrain = self.getTrainNumberFromSchedule(placeData["incomingSchedule"])

            # Add this one to visited because we'll visit it
            visited.add(placeId)
            # Make sure it is no longer in opened ones
            opened.remove(placeId)
           
            # Found what we searched -> escape from the loop
            if placeId == destinationId:
                break

            # Loop over each neighbour of the place <=> its departures
            for departureId in self.getDeparturesIdFromPlaceId(placeId):
                if departureId in visited: continue # Do not explore already visited places
                opened.add(departureId) # Add the place to explorated ones
                
                # Get the first train going to the specific departure 
                firstTrainAvailable = self.choseBestScheduleFromPlaceIdAndDepartureId(placeId,departureId,placeData["dayIndex"],placeData["ArrivalTime"],incomingTrain)

                                 

                # Get the right discriminant factor
                if query == "time":
                    # Minimise the time
                    discriminant = firstTrainAvailable["TimeOffset"]
                elif query == "distance":
                    # Minimise the distance
                    discriminant = self.getDistanceBetweenPlaceIdAndDepartureId(placeId,departureId)
                elif query =="mixed":
                    discriminant = firstTrainAvailable["TimeOffset"] * self.getDistanceBetweenPlaceIdAndDepartureId(placeId,departureId)
                else:
                    # Minimise the amount train stations crossed
                    discriminant = 1
                
                if self.getTrainNumberFromSchedule(firstTrainAvailable["Schedule"]) != incomingTrain:
                    discriminant *= self.postChoiceModifier

                
                # Discrimine
                if graph[departureId]["distance"] <= placeData["distance"] + discriminant:
                    continue 
                
                # Update the distance
                graph[departureId]["distance"] = placeData["distance"] + discriminant
                
                # Update everything else
                graph[departureId]["via"] = placeId # Useful to go back
                # Use to get the next available trains
                graph[departureId]["dayIndex"] = firstTrainAvailable["ResultingDay"] 
                # Use to get the next available trains
                graph[departureId]["ArrivalTime"] = firstTrainAvailable["Schedule"][1]
                # It's important to store data from the train, to get its reference for example
                graph[departureId]["incomingSchedule"] = firstTrainAvailable["Schedule"]
        
        return graph[destinationId]["distance"],self.getJourney(graph,originId,destinationId),graph[destinationId]["dayIndex"]-dayIndex

    # Day managing
    
    def getDayIndexFromDate(self,day,month) -> int:
        if month == self.referenceDate[1]:
            return day-self.referenceDate[0]  
        return self.monthLenghts[self.referenceDate[1]] - self.referenceDate[0] + day

    # Results visualization #

    def getJourney(self,graph,originId,destinationId) -> list:
        # Traceback the journey
        journey = []
        
        placeId = destinationId
        # Since the place isn't the origin, go back
        while placeId != originId:
            # Add to the journey the informations we want to get
            journey = self.getUsefulPlaceInformation(graph,placeId) + journey
            placeId = graph[placeId]["via"]
        # Add the final one <-> the origin
        return self.getUsefulPlaceInformation(graph,placeId) + journey 
    
    def getUsefulPlaceInformation(self,graph,placeId) -> list:
        return [[self.getNameFromPlaceId(placeId)] + [str(value) if value == graph[placeId]["dayIndex"] else value for value in graph[placeId].values() ]+ [placeId]] 
        
    def journeyToString(self,journey) -> str:
        # Get the stringfied journey in a list
        stringified = []
        # Stringify the journey
        for journeyPartIndex in range(len(journey)-1):
            stringified.append(f"Arrive à {journey[journeyPartIndex][3]} à {journey[journeyPartIndex][0]}, part à {journey[journeyPartIndex+1][4][0]} /{journey[journeyPartIndex+1][4][3]}/")
        # Stringify the last part of the journey (special case)
        stringified.append(f"Arrive à {journey[-1][3]} à {journey[-1][0]} : terminus")
        
        # Return the string corresponding
        return " ->\n".join(stringified)

    def journeyToSimplifiedString(self,journey) -> str:
        decoration = "\n=------------------------------------=\n"
        introducer = f"Voyage de {journey[0][0]} à {journey[-1][0]} en TER :\n"
        # Get the stringfied journey in a list
        stringified = []
        # Stringify the journey
        lastTrainNumber = ""
        for journeyPartIndex in range(len(journey)-1):
            trainNumber = self.extractTrainNumber(journey[journeyPartIndex+1][4][3])
            if trainNumber != lastTrainNumber:
                stringified.append(f"Arrive à {journey[journeyPartIndex][3]} à {journey[journeyPartIndex][0]}, part à {journey[journeyPartIndex+1][4][0]} /{trainNumber}/")
            lastTrainNumber = trainNumber
        # Stringify the last part of the journey (special case)
        stringified.append(f"Arrive à {journey[-1][3]} à {journey[-1][0]} : terminus")
        
        
        # Return the string corresponding
        return decoration + introducer + " ->\n".join(stringified) + decoration

    def extractTrainNumber(self,identifiant) -> str:
        return identifiant.split("ROUTIER")[0].split("FERRE")[0][2:]

    def getPath(self,originId,crossingIds,destinationId,dayIndex,hour,query) -> tuple:
        # All the Ids of the places on the path
        pathsIds = [originId] + crossingIds + [destinationId]
        # Store the whole data
        pathData = []
        pathLength = 0
        # Temporal informations
        formerHour = hour 
        formerDay = dayIndex
        for i in range(len(pathsIds)-1):
            # Compute a journey between a point on the path to an other
            intermediatePathLength,intermediatePathData,resultingDay = self.processDijkstra(pathsIds[i],pathsIds[i+1],formerDay,formerHour,query)
            # Update the temporal informations
            formerDay = int(intermediatePathData[-1][2])
            formerHour = intermediatePathData[-1][3]
            # Add the data to the whole date
            pathData += intermediatePathData[:-1] if i != len(pathsIds)-2 else intermediatePathData
            pathLength += intermediatePathLength
        
        return [pathLength,formerDay],pathData
    
    def getSimplifiedPath(self,originName,crossingNames,destinationName,date,hour,query) -> tuple:
        # All the Ids of the places on the path
        originId = self.getIdFromPlaceName(originName)
        crossingIds = [self.getIdFromPlaceName(crossingName) for crossingName in crossingNames]
        destinationId = self.getIdFromPlaceName(destinationName)
        assert originId != None and (not (None in crossingIds)) and destinationId != None, "Places' names aren't valid"
        
        dayIndex = self.getDayIndexFromDate(*[int(information) for information in date.split("/")])
        assert dayIndex >= 0, "Invalid date"
        
        return self.getPath(originId,crossingIds,destinationId,dayIndex,hour,query)[1]