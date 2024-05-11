import gui

#=======================#
# Either launch the GUI #

gui_instance = gui.GUI()
gui_instance.run()

#===========================#
# Either use the API itself #

parser = gui.api.TrainParser()
# Explicitly set the parseNeTEx parameter to True, if you want to load a new NeTEx file
parser.initialize(parseNeTEx=False,verbose=True)

data = parser.getSimplifiedPath(originName="Dinan",
                         crossingNames=[],
                         destinationName="Grenoble",
                         date="17/05",
                         hour="05:00:00",
                         query="time")

# Print the journey data
print(parser.journeyToSimplifiedString(data))