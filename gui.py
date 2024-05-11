import api
from api import StopPoint
api.os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import pygame.gfxdraw
import ctypes


def drawRoundedRect(screen,x,y,width,height,radius,border,main_color,background_color):
        # y adjustement for the texts
        y += int((42-height)/2)
        # Positions of the circles
        rect_pos = [[x,y],[x,y+height],[x+width,y+height],[x+width,y]]
        # Indicators of the border / radius to add or remove
        polygon_adjustments = [0,-radius,-radius,0,0,radius,radius,0]
        polygon_border = [border if not i//4 else -border for i in range(8)]
        corners_border = [border if not i//2 else -border for i in range(4)]
        
        # Draw the exterior corners 
        for pos in rect_pos:
            pygame.gfxdraw.filled_circle(screen,*pos,radius,main_color)
            pygame.gfxdraw.aacircle(screen,*pos,radius,main_color)
        
        # Draw the exterior polygon
        pygame.gfxdraw.filled_polygon(screen,[[rect_pos[i//2][0]+polygon_adjustments[i],rect_pos[i//2][1]+polygon_adjustments[(i+2)%8]] for i in range(8)],main_color)
        pygame.gfxdraw.polygon(screen,[[rect_pos[i//2][0]+polygon_adjustments[i],rect_pos[i//2][1]+polygon_adjustments[(i+2)%8]] for i in range(8)],main_color)
        
        # Draw the interior corners
        for i in range(4):
            pygame.gfxdraw.filled_circle(screen,rect_pos[i][0]+corners_border[i],rect_pos[i][1]+corners_border[(i+1)%4],radius,background_color)
            pygame.gfxdraw.aacircle(screen,rect_pos[i][0]+corners_border[i],rect_pos[i][1]+corners_border[(i+1)%4],radius,background_color)
        
        # Draw the interior polygon
        pygame.gfxdraw.filled_polygon(screen,[[rect_pos[i//2][0]+polygon_adjustments[i]+polygon_border[i],rect_pos[i//2][1]+polygon_adjustments[(i+2)%8]+polygon_border[(i+2)%8]] for i in range(8)],background_color)
        pygame.gfxdraw.polygon(screen,[[rect_pos[i//2][0]+polygon_adjustments[i]+polygon_border[i],rect_pos[i//2][1]+polygon_adjustments[(i+2)%8]+polygon_border[(i+2)%8]] for i in range(8)],background_color)

class GUI():
    def __init__(self):
        # Prevent pygame to modify the size of the window
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        
        # Initialising the window
        pygame.font.init()
        self.screen_width = 900
        self.format = 9/16
        self.screen_height = int(self.screen_width*self.format)
        self.screen = pygame.display.set_mode((900,self.screen_height))
        self.running = True
        
        # Linking the GUI to the API
        
        self.parser = api.TrainParser()
        parser_thread = api.threading.Thread(target=self.parser.initialize,group=None,daemon=False,args=(False,False))
        parser_thread.start()
        self.ready = False 
        
        self.init_graphics()
        self.init_slides()
        
    def init_graphics(self) -> None:
        # Define the colors
        self.main_color = (243,243,248)
        self.background_color = (12,19,31)
        self.discrete_color = (105,109,125)
        self.active_color = (141,232,254)
        self.colors = [self.main_color,self.background_color,self.discrete_color,self.active_color]
        
        # Enable the fonts
        self.fonts = {"32":pygame.font.Font("Icons/aeh.ttf",32),"38":pygame.font.Font("Icons/aeh.ttf",38)}

        # Get the icons
        icons = ["pin","check","clock","calendar","loop","download","map","stat"]
        self.icons = {icon:pygame.image.load(f"Icons/{icon}.png") for icon in icons}
        
        # Set up other pygame settings 
        self.icon = pygame.image.load("Icons/icon.png")
        pygame.display.set_icon(self.icon)
        pygame.display.set_caption("SNCF-TER")
        
    def init_slides(self) -> None:
        # Define the slides
        self.selected_slide ="loading" # "places_selection"
        self.slides = {"loading":Slide("loading",self.screen_width,self.colors,self.fonts,self.icons,self.parser)}
        # Variables to know when to display the cursor
        self.cursor_advancement = 0
        self.cursor_limit = 700
        # Used by the slides to know when does the user is clicking
        self.clicked = False
        self.clicked_cooldown = 20
        
    def event(self) -> None:
        # Reset the clicking state
        self.clicked = False
        if self.clicked_cooldown:
            self.clicked_cooldown -= 1
        
        for event in pygame.event.get():
            # Usual event, quit if asked
            if event.type == pygame.QUIT:
                self.running = False 
            # Send keybord inputs to the used slide
            if event.type == pygame.KEYDOWN:
                self.slides[self.selected_slide].keyInput(event)
            # Update the clicking state
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.clicked_cooldown == 0:
                    self.clicked = True
                    self.cursor_advancement = 0
                    self.clicked_cooldown = 20

    def run(self) -> None:
        while self.running:
            self.event()
            self.update()
            self.draw()
    
    def update(self) -> None:
        # Update the slides
        self.slides[self.selected_slide].update(self.clicked,self.parser.state)
        
        # Update the cursor
        self.cursor_advancement = (self.cursor_advancement + 1)%self.cursor_limit

        # Process each request
        self.process_requests()

    def process_requests(self) -> None:

        if self.parser.state == "Finished" and not self.ready:
            # Add extra slides
            self.slides = { "loading":Slide("loading",self.screen_width,self.colors,self.fonts,self.icons,self.parser),
                            "places_selection":Slide("places_selection",self.screen_width,self.colors,self.fonts,self.icons,self.parser),
                            "hour_selection":Slide("hour_selection",self.screen_width,self.colors,self.fonts,self.icons,self.parser),
                            "map":Slide("map",self.screen_width,self.colors,self.fonts,self.icons,self.parser),
                            "end_menu":Slide("end_menu",self.screen_width,self.colors,self.fonts,self.icons,self.parser)}
            self.selected_slide = "places_selection"
            self.ready = True
            
        # Change slide requests #
        for request in self.slides[self.selected_slide].requests["change_slide"]:
            self.slides[self.selected_slide].requests["change_slide"] = []
            # Change the slide tot the requested one  
            self.selected_slide = request
            
            # Update the size of the window
            if request == "map":
                pygame.display.set_mode((self.screen_width,self.screen_width))
            elif self.screen.get_size != (self.screen_width,self.screen_height):
                pygame.display.set_mode((self.screen_width,self.screen_height))
                
        
        # API call requests #
        for request in self.slides[self.selected_slide].requests["finalize"]:
            self.slides[self.selected_slide].requests["finalize"] = []
            # Get the places Ids
            originId = self.parser.getIdFromPlaceName(self.slides["places_selection"].fields[0].places[0])
            destinationId = self.parser.getIdFromPlaceName(self.slides["places_selection"].fields[1].places[0])

            # Get the extra informations
            hour = ":".join([text if len(text)==2 else "0"+text for text in self.slides["hour_selection"].time_fields[0].texts]+["00"])
            query = ["distance","time"][self.slides["hour_selection"].radio_buttons[0].selected]
            dayIndex = self.parser.getDayIndexFromDate(*[int(text) for text in self.slides["hour_selection"].time_fields[1].texts])
            
            # Call the API for a path, only save the path data
            path_index,self.path_data = self.parser.getPath(originId,[],destinationId,dayIndex,hour,query)

            # Also change the slide and update the end menu texts
            self.selected_slide = "end_menu"
            self.slides["end_menu"].free_texts[1].text = f"Arrivée à {self.path_data[-1][3]} à {self.path_data[-1][0][:12]+'...'*(len(self.path_data[-1][0]) >12)}"+ (f" (j+{path_index[1]-dayIndex})" if path_index[1] != dayIndex else "")
            self.slides["end_menu"].free_texts[1].recreate()
            # Create the corresponding map 
            self.slides["map"].maps[0].initialise(self.parser.stopPlaces,self.path_data)
        
        # Upload requests #
        for request in self.slides[self.selected_slide].requests["upload"]:
            self.slides[self.selected_slide].requests["upload"] = []
            with open("Exported/export.txt","w") as f:
                f.write(self.parser.journeyToSimplifiedString(self.path_data))
        for request in self.slides[self.selected_slide].requests["reset"]:
            self.slides[self.selected_slide].requests["reset"] = []
            self.selected_slide = "places_selection"
            self.slides["places_selection"] = Slide("places_selection",self.screen_width,self.colors,self.fonts,self.icons,self.parser)
            self.slides["hour_selection"] = Slide("hour_selection",self.screen_width,self.colors,self.fonts,self.icons,self.parser)
                            
    def draw(self) -> None:
        # Draw the background
        self.screen.fill(self.background_color)
        # Draw the slide elements   
        self.slides[self.selected_slide].draw(self.screen,self.cursor_advancement,self.cursor_limit)
        
        pygame.display.flip()

class Slide():
    def __init__(self,identifiant,screen_width,colors,fonts,icons,temp_parser):
        # Get the specific element
        self.id = identifiant 
        # Get the common elements
        self.screen_width = screen_width
        self.colors = colors 
        self.fonts = fonts 
        self.icons = icons
        self.days = temp_parser.dates
        
        self.requests = {"change_slide":[],"finalize":[],"upload":[],"reset":[]}
        self.createSlide(temp_parser)
    
    def createSlide(self,temp_parser) -> None:
        # For all the slides, this text appears
        self.free_texts = [FreeText(self.screen_width*0.05,self.screen_width*0.03,"SNCF TER",self.fonts["38"],self.colors,True,self.screen_width*0.01,None,False)]
        self.waiting_texts = []
        
        if self.id ==  "places_selection":
            # Two fields for origin and destination
            self.fields = [Field(int(self.screen_width/6),int(self.screen_width*0.15),int(self.screen_width/2.8),int(self.screen_width/30),temp_parser.placeNamesDict,"Départ de",self.fonts["32"],self.fonts["38"],self.colors,self.icons["pin"],self.icons["check"]),
                           Field(int(self.screen_width/6),int(self.screen_width*0.32),int(self.screen_width/2.8),int(self.screen_width/30),temp_parser.placeNamesDict,"Destination",self.fonts["32"],self.fonts["38"],self.colors,self.icons["pin"],self.icons["check"])]
            # A "Suivant" linked to the two fields
            self.send_buttons = [SendButton(0,int(self.screen_width*0.45),int(self.screen_width/4.5),int(self.screen_width/22.5),"Suivant",self.fonts["32"],self.colors,[0,1],[],["change_slide","hour_selection"],self.screen_width)]    
            # No more elements 
            self.time_fields = []
            self.radio_buttons = []
            self.surfaces = []
            self.maps = []
            
        elif self.id =="loading":
            self.waiting_texts = [WaitingText(self.screen_width*0.05,self.screen_width*0.47,self.fonts["38"],self.colors[0])]
            self.fields = []
            self.send_buttons = []
            self.time_fields = []
            self.radio_buttons = []
            self.surfaces = []
            self.maps = []
        elif self.id == "hour_selection":
            # Two time fields one for the hour and one for the date
            self.time_fields = [TimeField(int(self.screen_width/6),int(self.screen_width*0.15),50,20,"Heure du départ",self.fonts["32"],self.fonts["38"],self.colors,self.icons["clock"],self.icons["check"],"hour"),
                                TimeField(int(self.screen_width/6),int(self.screen_width*0.26),50,20,"Jour du départ ",self.fonts["32"],self.fonts["38"],self.colors,self.icons["calendar"],self.icons["check"],"date",self.days)]
            # A radio button to decide which query is expected
            self.radio_buttons = [RadioButton(int(self.screen_width/6),int(self.screen_width*0.37),50,20,"Rechercher par",["Temps","Distance"],self.fonts["38"],self.colors,self.icons["loop"])]
            # A send button linked to the time fields and to the radio button
            self.send_buttons = [SendButton(0,int(self.screen_width*0.45),int(self.screen_width/4.5),int(self.screen_width/22.5),"Suivant",self.fonts["32"],self.colors,[],[0,1],["finalize","yes"],self.screen_width)] 
            # No more elements
            self.maps = []
            self.fields = []
        elif self.id == "map":
            # A map of the path
            self.maps = [Map(0,0,self.screen_width,self.colors,self.fonts["32"])]
            # A go back button
            self.send_buttons=  [SendButton(0,int(self.screen_width*0.9),int(self.screen_width*0.6),int(self.screen_width/22.5),"Retour",self.fonts["32"],self.colors,[],[],["change_slide","end_menu"],self.screen_width)]
            self.time_fields = []
            self.radio_buttons = []
            self.fields = []
        elif self.id == "end_menu":
            # Three free texts, two of them are buttons for downloading and visualization
            self.free_texts.append(FreeText(int(self.screen_width/6),int(self.screen_width*0.15),"Arrivée à XXh40min à Brest",self.fonts["32"],self.colors,True,self.screen_width*0.003,self.icons["stat"],False))
            self.free_texts.append(FreeText(int(self.screen_width/6),int(self.screen_width*0.26),"Télécharger",self.fonts["32"],self.colors,False,self.screen_width*0.003,self.icons["download"],True,["upload","map"]))
            self.free_texts.append(FreeText(int(self.screen_width/6),int(self.screen_width*0.37),"Visualiser",self.fonts["32"],self.colors,False,self.screen_width*0.003,self.icons["map"],True,["change_slide","map"]))
            # Go back button 
            self.send_buttons=  [SendButton(0,int(self.screen_width*0.45),int(self.screen_width*0.6),int(self.screen_width/22.5),"Retour au début",self.fonts["32"],self.colors,[],[],["reset","reset"],self.screen_width)]
            
            # No more elements
            self.time_fields = []
            self.radio_buttons = []
            self.maps = []
            self.fields = []
            
    def draw(self,screen,cursor_advancement,cursor_limit) -> None:
        # Draw everything
        [path_map.draw(screen) for path_map in self.maps]
        [field.draw(screen,cursor_advancement,cursor_limit) for field in self.fields]
        [time_field.draw(screen) for time_field in self.time_fields]
        [send_button.draw(screen) for send_button in self.send_buttons] 
        [radio_button.draw(screen) for radio_button in self.radio_buttons] 
        [free_text.draw(screen) for free_text in self.free_texts]
        [waiting_text.draw(screen) for waiting_text in self.waiting_texts]
         
    def update(self,clicked,parser_state) -> None:
        # Reset requests
        self.requests = {"change_slide":[],"finalize":[],"upload":[],"reset":[]}
        
        # Update and get requests from buttons
        [self.requests[request[0]].append(request[1]) for request in [send_button.update(clicked) for send_button in self.send_buttons] if request]
        [self.requests[request[0]].append(request[1]) for request in [free_text.update(clicked) for free_text in self.free_texts] if request]
        
        # Update other elements
        [path_map.update() for path_map in self.maps]
        [field.update(pygame.mouse.get_pos(),clicked) for field in self.fields]
        [time_field.update(pygame.mouse.get_pos(),clicked) for time_field in self.time_fields]
        [radio_button.update(clicked) for radio_button in self.radio_buttons]
        [waiting_text.update(parser_state) for waiting_text in self.waiting_texts]

    def keyInput(self,event) -> None:
        # Send key inputs to elements
        [field.processEvent(event) for field in self.fields]
        [time_field.processEvent(event) for time_field in self.time_fields]
        
        # Update the send button which can be linked to fields and time fields
        [send_button.test_validity([self.fields[index].valid for index in send_button.fields_indices]+[self.time_fields[index].valid for index in send_button.time_fields_indices]) for send_button in self.send_buttons]

class WaitingText():
    def __init__(self,x,y,font,color):
        # Get common elements
        self.x = x 
        self.y = y 
        self.font = font 
        self.color = color
        
        # What is displayed
        self.text = "" 
        self.rendered_text = self.font.render(self.text,True,self.color)
        # ... counter
        self.count = 0
        self.last_count = 0

    def update(self,parser_state) -> None:
        self.count += 1
        if self.count >= 400: self.count = 0
        
        # Only rerender when the new state is different
        if parser_state == self.text and self.last_count//100 == self.count//100:
            return 
        # Render the new text
        self.text = parser_state
        self.rendered_text = self.font.render(self.text+"."*(self.count//100),True,self.color)
        self.last_count = self.count
    
    def draw(self,screen) -> None:
        screen.blit(self.rendered_text,(self.x,self.y))

class Field():
    def __init__(self,x,y,width,height,places_names,introducer_text,font,huge_font,colors,pin,check):
        # Get common elements
        self.x = x 
        self.y = y 
        self.width = width 
        self.height = height
        self.places_names = places_names
        self.pin = pin # First icon before the introducer text
        self.check = check # This icon only shows up when the entered text is valid
    
        # Redefine colors and fonts
        self.main_color = colors[0]
        self.background_color = colors[1]
        self.discrete_color = colors[2]
        self.active_color = colors[3]
        self.font = font 
        self.huge_font = huge_font
        
        # Render and get the position of the text before the field itself
        self.introducer_text = introducer_text 
        self.rendered_introducer_text = self.huge_font.render(self.introducer_text,True,self.main_color)
        self.introducer_offset = int(self.width*0.8) 
        self.introducer_y = int(self.y+7+self.height/2-self.huge_font.size(self.introducer_text)[1]/2)
        
        # Render the entered text
        self.text = ""
        self.rendered_text = self.font.render(self.text,True,self.main_color)
        
        # Render the autocompletion
        self.completion = ""
        self.rendered_completion = self.font.render(self.completion,True,self.discrete_color)
        self.completion_offset = 0
        
        # Render the cursor
        self.rendered_cursor = self.font.render("|",True,self.main_color)
        
        # Other variables
        self.colliding = False # The mouse is over the field
        self.focused = False # The user has clicked on the field
        self.valid = False # The entered text is valid
        self.places = [] # The valid places names

    def processEvent(self,event) -> None:
        # Do not process any event if the field isn't even focused
        if not self.focused:
            return 
        
        # For the usual chars, just add it to the text
        if event.key not in [pygame.K_RETURN,pygame.K_BACKSPACE,pygame.K_SPACE,pygame.K_TAB]:
            self.text += event.unicode
        # For the backspace remove the last char
        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        # For the space, only add space if the last char isn't a space and if the text isn't empty
        elif event.key == pygame.K_SPACE: 
            if self.text:
                self.text += " " if self.text[-1] != " " else ""
        # For the return key : complete the text with the completion suggested
        elif event.key == pygame.K_RETURN or event.key == pygame.K_TAB:
            self.text += self.getCompletion(self.text)

        # Get the places corresponding to the entered text
        self.places = [place for place in self.places_names.keys() if place.lower().replace("î","i").replace("â","a") == self.text.lower().strip()]
        # The text field is valid if the places corresponding text isn't an empty list, else it takes the first element
        self.valid = False if not self.places else self.places[0]
        
        # Update the rendered text
        self.updateRenderedText()
    
    def updateRenderedText(self) -> None:
        # Get only the last 16 chars of the text
        cropped_text = self.transformText(self.text,16)
        self.rendered_text = self.font.render(cropped_text,True,self.main_color)
        # Change the offset of the completion to be according to the text displayed
        self.completion_offset = self.font.size(cropped_text)[0]
        # Get a completion slightly bigger than the entered text (two chars longer)
        self.completion = self.getCompletion(self.text)[0:18-min(16,len(self.text))]
        self.rendered_completion = self.font.render(self.completion,True,self.discrete_color)

    def unfocusRenderedText(self) -> None:
        # If the text becomes unfocused, get only the 16 first char and add ... if it's in realty longer
        self.rendered_text = self.font.render(self.text[0:16]+"..."*(self.text[0:16]!=self.text),True,self.main_color)
        # Do not render any completion 
        self.completion = ""
        self.rendered_completion = self.font.render(self.completion,True,self.discrete_color)

    def transformText(self,text,limit) -> str:
        # Returns the last 16 char of the text
        return text[max([0,len(text)-limit]):max([0,len(text)-limit])+limit]

    def getCompletion(self,text) -> dict:
        # Don't return a completion suggestion if the text is empty
        if not text: return ""
        
        # Modify the text
        loweredText = text.lower()
        textLength = len(loweredText)
        
        # For a given text of length n
        # Get the places where the n first chars are in common with the entered text (everything lowered)
        # Sort by the number of departures in decreasing order
        places = sorted([(placeName,placeInfo[1]) for placeName,placeInfo in self.places_names.items() if loweredText == placeName[:textLength].lower().replace("î","i").replace("â","a")],key=lambda x:x[1],reverse=True)

        # Return an empty string if no place has been found
        if not places:
            return ""
        
        # Return the completion 
        return places[0][0][textLength:]
         
    def draw(self,screen,cursor_advancement,cursor_limit) -> None:
        # Draw the rounded rect around the entered text 
        drawRoundedRect(screen, self.introducer_offset+self.x-5,self.y,self.width,self.height,20,5,self.active_color if self.colliding else self.main_color,self.background_color)
       
        # Draw the texts 
        screen.blit(self.rendered_introducer_text,(self.x,self.introducer_y))
        screen.blit(self.rendered_completion,(self.introducer_offset+self.x+self.completion_offset,self.y))
        screen.blit(self.rendered_text,(self.introducer_offset+self.x,self.y))
        
        # Draw the cursor, half the time
        if cursor_advancement <cursor_limit/2 and self.focused: screen.blit(self.rendered_cursor,(self.introducer_offset+self.x+self.completion_offset,self.y))
        
        # Draw the icons
        screen.blit(self.pin,(self.x-self.width/5,self.y))
        if self.valid: screen.blit(self.check,(self.x+self.width*2,self.y))
        
    def update(self,mouse_position,clicked) -> None:
        # Get if the mouse is colliding
        self.colliding = pygame.rect.Rect(self.introducer_offset+self.x-5-20,self.y+7-20,self.width+40,self.height+40).collidepoint(mouse_position)
        
        if not clicked:
            return 
        
        # If clicked and colliding -> the field is focused
        self.focused =  self.colliding 
        
        # If turned into focused -> update the text
        if self.focused:
            self.updateRenderedText()
        # If it's unfocusing, add a capital letter at the beginning of the entered text
        else:
            if self.text: self.text = self.text[0].upper() + self.text[1:]
            self.unfocusRenderedText()

class TimeField():
    def __init__(self,x,y,width,height,introducer_text,font,huge_font,colors,clock,check,function,limit_days=""):
        # Get common elements
        self.x = x 
        self.y = y 
        self.width = width 
        self.height = height
        self.clock = clock
        self.check = check
        self.limits = [23,59] if function == "hour" else [31,12] # Max entered values
        self.availables = "01232456789" # Chars allowed 
        self.limit_days = limit_days
        
        # Redefine colors and fonts
        self.main_color = colors[0]
        self.background_color = colors[1]
        self.discrete_color = colors[2]
        self.active_color = colors[3]
        self.font = font 
        self.huge_font = huge_font
        
        # Render and get the position of the text before the field itself
        self.introducer_text = introducer_text
        self.rendered_introducer_text = self.huge_font.render(self.introducer_text,True,self.main_color)
        self.introducer_offset = int(self.width*7)
        self.introducer_y = int(self.y+7+self.height/2-self.huge_font.size(self.introducer_text)[1]/2)
        
        # Render the entered text and the indications
        self.texts = ["",""]
        self.rendered_texts = [self.font.render(self.texts[0],True,self.main_color),self.font.render(self.texts[1],True,self.main_color)]
        self.indications = ["17","30"] if function == "hour" else ["28","06"]
        self.rendered_indications = [self.font.render(self.indications[0],True,self.discrete_color),self.font.render(self.indications[1],True,self.discrete_color)]
        
        # Elements and variables in between the two fields
        self.minutes_offset = self.width*3 # Space between the two fields
        # What is between
        self.separator = self.huge_font.render(":" if function == "hour" else "/",True,self.main_color)    
        
        # Other variables
        self.function = function # Determine whether it is for the hour or for the date
        self.colliding = [False,False] # Colliding state of the two fields
        self.focused = [False,False] # Focusing state of the two fields
        self.valid = False  
        self.selected = 0 # Determine which of the two fields is selected
        self.monthly_limits = [31,28,31,30,31,30,31,31,30,31,30,31] # Month lenghts

    def processEvent(self,event) -> None:
        # If none of the fields is focused, don't process the events
        if not (True in self.focused):
            return
        
        # Numerical char, and the length isn't greater than one
        if event.unicode in self.availables and len(self.texts[self.selected])<2 and event.unicode:
            #If the text is only a zero, just erase it by the entered number
            if self.texts[self.selected] == "0":
                self.texts[self.selected] = event.unicode 
            # Else add the number if it respects the limitations in function of the function
            else:         
                self.texts[self.selected] += event.unicode if self.applyLimitations(event) else ""
        # Backspace juste removes the last char
        elif event.key == pygame.K_BACKSPACE:
            self.texts[self.selected] = self.texts[self.selected][:-1]
        
        # The field itself is valid if none of the subfields are empty
        self.valid = (bool(self.texts[0]) and bool(self.texts[1]))
        # The date timefield has a special property : the entered date must be after the dataset date
        if self.valid and self.function != "hour":
            day = (("0" if len(self.texts[1])==1 else "") + self.texts[1] + ("0" if len(self.texts[0])==1 else "") + self.texts[0])
            self.valid = day > self.limit_days[0]
        # Updat the rendered text
        self.updateRenderedText()
    
    def applyLimitations(self,event) -> bool:
        tested = int(self.texts[self.selected] + event.unicode)        

        # First case we're looking for hours and minutes, so the time has just to be under the limit 
        if self.function == "hour":
            return tested <= self.limits[self.selected]
        
        # Second case it's for a date

        # If it's for the month, just test if the month is valid (>0 and < 13)
        if self.selected == 1:
            month_valid = tested <= self.limits[1] and tested > 0
            # If the month is valid, apply the limitation on the day
            # For example go from 31 / 00 asks for 31 / 02 and gives 28/02
            if month_valid and self.texts[0]:
                self.texts[0] = str(min(int(self.texts[0]),self.monthly_limits[tested-1]))
            return month_valid

        # Just test if the tested is under the max limit and over 0 if there is no month
        if not self.texts[1]:
            return tested <= 31 and tested > 0

        # Crop the day to the month limit
        return tested <= self.monthly_limits[int(self.texts[1])-1] and tested > 0

    def updateRenderedText(self) -> None:
        # Render the text and add a zero before it, if it is only one char long
        self.rendered_texts = [self.font.render("0"*(len(self.texts[0]) == 1)+self.texts[0],True,self.main_color),
                               self.font.render("0"*(len(self.texts[1]) == 1)+self.texts[1],True,self.main_color)]
        
        # Only render the indications if the texts are empty
        self.rendered_indications = [self.font.render(self.indications[0] if not self.texts[0] else "",True,self.discrete_color),
                                     self.font.render(self.indications[1] if not self.texts[1] else "",True,self.discrete_color)]
        
    def draw(self,screen) -> None:
        # Draw both of the subfields
        drawRoundedRect(screen, self.introducer_offset+self.x-5,self.y,self.width,self.height,20,5,self.active_color if self.focused[0] or self.colliding[0] else self.main_color,self.background_color)
        drawRoundedRect(screen, self.introducer_offset+self.x-5+self.minutes_offset,self.y,self.width,self.height,20,5,self.active_color if self.focused[1] or self.colliding[1] else self.main_color,self.background_color)

        # Draw all the texts
        screen.blit(self.rendered_introducer_text,(self.x,self.introducer_y))
        screen.blit(self.rendered_indications[0],(self.introducer_offset+self.x,self.y))
        screen.blit(self.rendered_indications[1],(self.introducer_offset+self.x+self.minutes_offset,self.y))
        screen.blit(self.rendered_texts[0],(self.introducer_offset+self.x,self.y))
        screen.blit(self.rendered_texts[1],(self.introducer_offset+self.x+self.minutes_offset,self.y))
        screen.blit(self.separator,(self.x+self.width*8.8,self.introducer_y))   
        
        # Draw the icons
        screen.blit(self.clock,(self.x-self.width*1.5,self.y-self.width*0.05)) 
        if self.valid: screen.blit(self.check,(self.x+self.width*12,self.y))

    def update(self,mouse_position,clicked) -> None:
        # Get if the mouse is colliding with one of the fields
        self.colliding = pygame.rect.Rect(self.introducer_offset+self.x-5-20,self.y+7-20,self.width+40,self.height+40).collidepoint(mouse_position),pygame.rect.Rect(self.introducer_offset+self.x-5-20+self.minutes_offset,self.y+7-20,self.width+40,self.height+40).collidepoint(mouse_position)
        
        if not clicked:
            return 
        
        # If clicking, the focusing states are the same as the colliding ones
        self.focused = self.colliding
        
        # If one of the subfields are focused, change the selected value 
        if True in self.focused:
            self.selected = self.focused.index(True)
        
        # Finally render the text
        self.updateRenderedText()

class RadioButton():
    def __init__(self,x,y,width,height,introducer_text,choices,font,colors,loop):
        # Get common elements
        self.x = x 
        self.y = y 
        self.width = width 
        self.height = height
        self.loop = loop
        self.selected = 1 # tell which choice is selected

        # Redefine the colors and the fonts
        self.main_color = colors[0]
        self.background_color = colors[1]
        self.discrete_color = colors[2]
        self.active_color = colors[3]
        self.font = font 
        self.introducer_text = introducer_text
        
        # Set up the introducer text 
        self.introducer_y = int(self.y+7+self.height/2-self.font.size(self.introducer_text)[1]/2)
        self.rendered_introducer_text = self.font.render(self.introducer_text,True,self.main_color)
        self.introducer_offset = int(self.width*7)
        
        # Render the choices
        self.rendered_choices = [[self.font.render(choice,True,self.main_color),self.font.render(choice,True,self.active_color)] for choice in choices]
    
        # Collision managing 
        self.colliding = [0,0]
        self.collisions_rects = [pygame.rect.Rect(self.x+self.width*6.4,self.introducer_y,*self.rendered_choices[0][0].get_size()),
                                 pygame.rect.Rect(self.x+self.width*10.4,self.introducer_y,*self.rendered_choices[1][0].get_size())]
        self.balls_pos = [[self.x+self.width*6,int(self.width*0.4+self.y)],[self.x+self.width*10,int(self.width*0.4+self.y)]]

    def draw(self,screen) -> None:
        # Draw the texts
        screen.blit(self.rendered_introducer_text,(self.x,self.introducer_y))
        screen.blit(self.rendered_choices[0][self.selected or self.colliding[0]],(self.x+self.width*6.4,self.introducer_y))
        screen.blit(self.rendered_choices[1][not self.selected or self.colliding[1]],(self.x+self.width*10.4,self.introducer_y))
        
        # Draw the first dot : unselected
        pygame.gfxdraw.filled_circle(screen,*self.balls_pos[self.selected],int(self.width*0.12),self.main_color)
        pygame.gfxdraw.aacircle(screen,*self.balls_pos[self.selected],int(self.width*0.12),self.main_color)
        
        # Draw the second dot : selected
        pygame.gfxdraw.filled_circle(screen,*self.balls_pos[not self.selected],int(self.width*0.16),self.active_color)
        pygame.gfxdraw.filled_circle(screen,*self.balls_pos[not self.selected],int(self.width*0.12),self.background_color)
        pygame.gfxdraw.aacircle(screen,*self.balls_pos[not self.selected],int(self.width*0.12),self.active_color)
        pygame.gfxdraw.aacircle(screen,*self.balls_pos[not self.selected],int(self.width*0.16),self.active_color)

        # Draw the icon 
        screen.blit(self.loop,(self.x-self.width*1.5,self.y-self.width*0.05)) 
        
    def update(self,clicked) -> None:
        # Get if the mouse is colliding with one of the choices
        self.colliding = [rect.collidepoint(pygame.mouse.get_pos()) for rect in self.collisions_rects]
        
        # If colliding and clicking, change the selection
        if True in self.colliding and clicked:
            self.selected = not self.colliding.index(True)

class SendButton():
    def __init__(self,x,y,width,height,text,font,colors,fields_indices,time_fields_indices,action,centered=False):
        # Get common elements
        self.x = x if not centered else int(centered/2-width/2) # Center if expected
        self.y = y  
        self.width = width
        self.height = height 
        self.available = False if fields_indices or time_fields_indices else True # State of the button
         
        # Get colors and fonts
        self.font = font
        self.colors = colors
        self.selected_color = self.colors[0] # Associated color to the availability and the colliding state
        
        # Render the text
        self.text = text 
        self.rendered_available = self.font.render(self.text,True,self.colors[1])
        self.rendered_unavailable = self.font.render(self.text,True,self.colors[2])
        self.text_pos = self.x + self.width/2 - self.font.size(self.text)[0]/2, self.y + self.height/2 - self.font.size(self.text)[1]/2
        
        # Action of the button and fields related to the button
        self.action = action
        self.fields_indices = fields_indices
        self.time_fields_indices = time_fields_indices
        
        # Collision detection
        self.radius = int(self.height/2)
        self.collision_rect = pygame.rect.Rect(self.x-self.radius,self.y,self.width+self.radius*2,self.height)
        self.colliding = False
        
    def draw(self,screen) -> None:
        # Draw the center rect
        pygame.gfxdraw.aapolygon(screen,[[self.x,self.y],[self.x,self.y+self.height],[self.x+self.width,self.y+self.height],[self.x+self.width,self.y]],self.selected_color)
        pygame.gfxdraw.filled_polygon(screen,[[self.x,self.y],[self.x,self.y+self.height],[self.x+self.width,self.y+self.height],[self.x+self.width,self.y]],self.selected_color)
        # Draw circles at both the ends
        pygame.gfxdraw.aacircle(screen,self.x,self.y+self.radius,self.radius,self.selected_color)        
        pygame.gfxdraw.aacircle(screen,self.x+self.width,self.y+self.radius,self.radius,self.selected_color)   
        pygame.gfxdraw.filled_circle(screen,self.x,self.y+self.radius,self.radius,self.selected_color)        
        pygame.gfxdraw.filled_circle(screen,self.x+self.width,self.y+self.radius,self.radius,self.selected_color)   
        # Draw the text
        screen.blit(self.rendered_available if self.available else self.rendered_unavailable,self.text_pos)

    def update(self,clicked) -> tuple:
        # Get if the mouse is colliding with the button
        self.colliding = self.collision_rect.collidepoint(pygame.mouse.get_pos())
        # Change the color of the button in function of the availibity and the colliding state
        self.selected_color = self.colors[3] if self.colliding and self.available else self.colors[0]
        # If the button is available and the user has clicked, send the action to the requests
        return self.action if clicked and self.colliding and self.available else ""

    def test_validity(self,validities) -> None:
        self.available = not (False in validities)

class FreeText():
    def __init__(self,x,y,text,font,colors,underlinded,lining,icon,is_button=False,action=""):
        # Get common elements
        self.x = int(x) 
        self.y = int(y)
        self.icon = icon
        self.is_button = is_button
        
        # Redefine the colors and the fonts
        self.font = font
        self.colors = colors
        self.main_color = self.colors[0]
        
        # Set up the text
        self.text = text
        self.rendered_text = font.render(self.text,True,self.main_color)
        self.text_width,self.text_height = self.font.size(self.text)
        
        # Set up the underline
        self.underlined = underlinded # State of the text
        self.excedent = min(15,int(self.text_width * 0.05)) # Additional length of the underline
        self.lining =int(lining) # Line width
        self.line_offset = int(self.text_height*1.05) # Line y offset to the text
        self.end_radius = int(self.lining/2) # Size of the end circles
        # Drawn rect of the underline
        self.underline_rect = [[self.x-self.excedent,self.y+self.line_offset],
                               [self.x+self.excedent+self.text_width,self.y+self.line_offset],
                               [self.x+self.excedent+self.text_width,self.y+self.line_offset+self.lining],
                               [self.x-self.excedent,self.y+self.line_offset+self.lining],
                               ]
        
        # Collision 
        self.collision_rect = pygame.rect.Rect(self.x-self.text_width*0.05,self.y-self.text_height*0.05,self.text_width*1.1,self.text_height*1.1)
        self.colliding = False
        self.action = action # What is returned if it is a button and it's both colliding and clicking
    
    def recreate(self) -> None:
        # Set up the text
        self.rendered_text = self.font.render(self.text,True,self.main_color)
        self.text_width,self.text_height = self.font.size(self.text)
        
        # Set up the underline
        self.excedent = min(15,int(self.text_width * 0.05)) # Additional length of the underline
        self.line_offset = int(self.text_height*1.05) # Line y offset to the text
        self.end_radius = int(self.lining/2) # Size of the end circles
        # Drawn rect of the underline
        self.underline_rect = [[self.x-self.excedent,self.y+self.line_offset],
                               [self.x+self.excedent+self.text_width,self.y+self.line_offset],
                               [self.x+self.excedent+self.text_width,self.y+self.line_offset+self.lining],
                               [self.x-self.excedent,self.y+self.line_offset+self.lining],
                               ]
        
        # Collision 
        self.collision_rect = pygame.rect.Rect(self.x-self.text_width*0.05,self.y-self.text_height*0.05,self.text_width*1.1,self.text_height*1.1)
          
    def draw(self,screen) -> None:
        # Draw the icon at the left
        if self.icon:
            screen.blit(self.icon,(self.x-75,self.y))
        # Draw the text itself
        screen.blit(self.rendered_text,(self.x,self.y))
        # Eventually draw the underline
        if self.underlined or self.colliding:
            # Main rect of the underline
            pygame.gfxdraw.filled_polygon(screen,self.underline_rect,self.main_color)
            pygame.gfxdraw.aapolygon(screen,self.underline_rect,self.main_color)
            # Ends of the underline
            pygame.gfxdraw.filled_circle(screen,self.x-self.excedent,self.y+self.line_offset+self.end_radius,+self.end_radius,self.main_color)
            pygame.gfxdraw.aacircle(screen,self.x-self.excedent,self.y+self.line_offset+self.end_radius,+self.end_radius,self.main_color)
            pygame.gfxdraw.filled_circle(screen,self.x+self.excedent+self.text_width,self.y+self.line_offset+self.end_radius,+self.end_radius,self.main_color)
            pygame.gfxdraw.aacircle(screen,self.x+self.excedent+self.text_width,self.y+self.line_offset+self.end_radius,+self.end_radius,self.main_color)

    def update(self,clicked) -> tuple:
        # Do not update the text if it's not a button
        if not self.is_button: return ""
        # Get if the mouse is colliding with the text
        self.colliding = self.collision_rect.collidepoint(pygame.mouse.get_pos())
        # If it is and the user has clicked send the action to the requests
        return self.action if clicked and self.colliding else ""

class Map():
    def __init__(self,x,y,screen_width,colors,font):
        # Get common elements 
        self.x = x 
        self.y = y 
        self.screen_width = screen_width
        self.width = int(self.screen_width*0.9)
        self.offsets = [int(self.screen_width*0.05),int(self.screen_width*0.05*1.5)]
        self.colors = colors
        self.font = font 
        
        # Map specific elemets
        self.surface = pygame.Surface((self.width,self.width))
        self.points = [] # All the train stations
        self.closest_point = False # Closest train station to the mouse
        self.journey = None # Journey data
        
        self.rendered_texts = [None,None] # Closest train station name and arrival time
        self.texts_offset = [0,0] # Respective offsets

    def draw(self,screen) -> None:
        # Draw the surface
        screen.blit(self.surface,(self.offsets))
        # If there is a closest point draw it and its text
        if self.closest_point:
            pygame.draw.circle(screen,self.colors[2],self.closest_point[1:3],5)
            screen.blit(self.rendered_texts[0],(self.texts_offset[0],self.screen_width*0.03))
            screen.blit(self.rendered_texts[1],(self.texts_offset[1],self.screen_width*0.08))
    
    def initialise(self,places,journey) -> None:
        # Fill the background
        self.surface.fill(self.colors[1])
        
        # Get the boundaries of the map
        miny, maxy = 53, 41.9193076 # Latitudes ones
        ofy = maxy - miny 
        
        minx,maxx = -6.2468075, 9.1656815 # Longitudes ones
        ofx = maxx - minx
        
        # Get the journey stations as stopPoint instances
        journeysStations = [places[journeyPart[-1]] for journeyPart in journey]
        
        # For each train station get its x and y coordinate and draw it on the map
        for stopPoint in places.values():
            # Lerp
            x =  int(self.width* (float(stopPoint.Location[0])-minx)/ofx)
            y =  int(self.width*(float(stopPoint.Location[1])-miny)/ofy)-70
            # Draw on the map
            pygame.gfxdraw.filled_circle(self.surface,x,y,7,(243,243,248,20))

        # Draw the segments between the points of th journey
        for journeyIndex in range(len(journeysStations)-1):
            # Get the starting position
            x =  int(self.width* (float(journeysStations[journeyIndex].Location[0])-minx)/ofx)
            y =  int(self.width*(float(journeysStations[journeyIndex].Location[1])-miny)/ofy)-70
            # Get the destination position
            x_destination = int(self.width* (float(journeysStations[journeyIndex+1].Location[0])-minx)/ofx)
            y_destination =  int(self.width*(float(journeysStations[journeyIndex+1].Location[1])-miny)/ofy)-70
            
            # Draw the segment on the map
            pygame.draw.line(self.surface,self.colors[3],(x,y),(x_destination,y_destination),5)
            # Add the point (in pixel coordinates) to the points list 
            self.points.append([journeysStations[journeyIndex].Name,x+self.offsets[0],y+self.offsets[1],journey[journeyIndex][3]])
        # Add the last point (in pixel coordinates) to the points list 
        self.points.append([journeysStations[-1].Name,x_destination+self.offsets[0],y_destination+self.offsets[1],journey[-1][3]])
        
        # Get the closest point as the first one, render its texts
        self.closest_point = self.points[0]
        self.rendered_texts[0] = self.font.render(self.closest_point[0][:20] + ("..." if len(self.closest_point[0])>20 else ""),True,self.colors[2]) 
        self.rendered_texts[1] = self.font.render(self.closest_point[-1],True,self.colors[2]) 
        # Center the texts by modifying their offsets
        self.texts_offset[0] = self.screen_width/2 - self.font.size(self.closest_point[0])[0]/2
        self.texts_offset[1] = self.screen_width/2 - self.font.size(self.closest_point[-1])[0]/2

        # Save the journey
        self.journey = journey

    def update(self) -> None:
        # Temporary save the last closest point
        last_point = self.closest_point
        # Get the new closest point
        self.closest_point = sorted(self.points,key=lambda point:self.get_distance(point[1:3],pygame.mouse.get_pos()) )[0]
        
        # If it is at a distance bigger than 50px, don't use it
        if self.get_distance(self.closest_point[1:3],pygame.mouse.get_pos()) > 50:
            self.closest_point = False 
            return 

        if last_point == self.closest_point:
            return
        
        # If the new closest point is different from the last one, change the texts
        self.rendered_texts[0] = self.font.render(self.closest_point[0][:20]+("..." if len(self.closest_point[0])>20 else ""),True,self.colors[2]) 
        self.rendered_texts[1] = self.font.render(self.closest_point[-1],True,self.colors[2])
        # Center the texts
        self.texts_offset[0] = self.screen_width/2 - self.font.size(self.closest_point[0])[0]/2
        self.texts_offset[1] = self.screen_width/2 - self.font.size(self.closest_point[-1])[0]/2

    def get_distance(self,pos,mouse_pos) -> float:        
        return api.math.sqrt((pos[0]-mouse_pos[0])**2+(pos[1]-mouse_pos[1])**2)
  