import os

### Helical Coordinate Conversion and Filament ID Re-assignment

### To accommodate the local curvature and flexible bending of helical fibrils during picking in cryoSPARC, continuous filaments were artificially segmented at short intervals (every 10 particles). 

### To transfer coordinates to RELION and restore physical filament continuity, a two-step custom Python pipeline was developed:

### 1. **Coordinate & Format Conversion:**
###    Initial cryoSPARC (`.cs`) metadata were converted using PyEM (`csparc2star.py`). A custom Python script reformatted the metadata, performed Y-axis coordinate inversion, and split particle coordinates into ### individual STAR files per micrograph (`_csfID_output`).

### 2. **Spatial Alignment & Half-Set Reset:**
###   Following particle extraction and classification in RELION, a second Python script using spatial nearest-neighbor search (`scipy.spatial.KDTree`) mapped extracted particles back to their original micrograph-level reference files. This step restored the unified `_rlnHelicalTubeID` for each physically continuous fibril. Crucially, the `_rlnRandomSubset` metadata field was removed to force RELION to perform a fresh, unbiased half-map assignment based strictly on true physical filaments, avoiding cross-talk between half-maps during FSC estimation.



###Validation & Impact:
###    Testing confirmed that maps reconstructed before and after this ID correction showed a map correlation of 0.99, with a negligible resolution difference of only ~0.1 Å, validating both structural integrity and data consistency.



file_path = input("Input the name of the star file: ") 
output_folder = file_path[:-5] + "_csfID_output"

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
	os.makedirs(output_folder)

# Read data from the file
with open(file_path, 'r') as file:
	data_r_star = file.read()

# Process each line in the data
for line in data_r_star.split('\n'):
	if line.startswith("000"):
		# Extract image name and coordinates
		CoordinateX3, CoordinateY4, HelicalTubeID14,  ImageName1, MicrographName2 = float(line.split()[2]), float(line.split()[3]), line.split()[13],  line.split()[0], line.split()[1]
	
	# Create star file in the output folder
		image_name = MicrographName2[41:-31]+".star"
		star_file_path = os.path.join(output_folder, image_name.replace(".mrc", ".star"))


		if os.path.exists(star_file_path):
			# If it exists, append the coordinates
			with open(star_file_path, 'a') as star_file:
				star_file.write(f"{CoordinateX3} {4096-CoordinateY4}  2   -999.00000   -999.00000 {HelicalTubeID14}\n")
		else:
			# If it doesn't exist, create the star file and write coordinates
			with open(star_file_path, 'w') as star_file:
				star_file.write("# version 30001\n\ndata_\n\nloop_\n_rlnCoordinateX #1 \n_rlnCoordinateY #2 \n_rlnParticleSelectionType #3 \n_rlnAnglePsi #4 \n_rlnAutopickFigureOfMerit #5 \n_rlnHelicalTubeID #6\n")
				star_file.write(f"{CoordinateX3} {4096-CoordinateY4}  2   -999.00000   -999.00000 {HelicalTubeID14}\n")
		#print("Star files "+star_file_path+" created and updated successfully..")
			
		

print(file_path[:-5]+" is done")
