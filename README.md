# A french TER path finder using SNCF NeTEx files
- Download the raw data from [data.gouv.fr](data.gouv.fr) and replace [sncf_netexfr_YYYYYMMDD_2305.xml](https://github.com/EwannAnacombesque/DeTERmine/blob/main/sncf_netexfr_20240509_2305.xml). 
- You can have access to the shortest (in term of time or distance) path from a train station to an other, only using TERs.
- Use the __API__ or the __GUI__ to obtain your journey.
- Only hardload the NeTEx file once, unless you want to __update__ the data.
- The data is only valid for the *30 next days* after the download date.
## An example of a journey in TER from Dinan to Grenoble the 17/05/24
```
=------------------------------------=
Voyage de Dinan à Grenoble en TER :
Arrive à 05:00:00 à Dinan, part à 05:58:00 /854104/ ->
Arrive à 06:18:00 à Dol-de-Bretagne, part à 06:43:00 /854304/ ->
Arrive à 07:25:00 à Rennes, part à 07:36:00 /858307/ ->
Arrive à 08:52:00 à Nantes, part à 09:16:00 /860108/ ->
Arrive à 10:57:00 à Tours, part à 12:04:00 /16840/ ->
Arrive à 17:52:00 à Lyon Part Dieu, part à 18:16:00 /17633/ ->
Arrive à 19:39:00 à Grenoble : terminus
=------------------------------------=
```
# GUI
- I decided to mimic the graphical charter of [sncf-connect.fr](sncf-connect.fr)
- The font used is the Avenir Font
- The icons come from [fontawesome.com](fontawesome.com)
- Everything else is made with pygame by me
