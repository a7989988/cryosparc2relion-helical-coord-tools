file_path = "J118_particles.star"
output_folder = "J118_particles_output"
Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
os.makedirs(output_folder)
cw = 0
ck = 0
l = 0
Read data from the file
with open(file_path, 'r') as file:
data_r_star = file.read()
image_name_old = "none"
HelicalTubeID14_old = 0
====== Dynamic STAR Header Parsing ======
col_idx = {}
for line in data_r_star.split('
'):
line = line.strip()
# RELION star file headers start with _rln
if line.startswith('_rln'):
parts = line.split()
if len(parts) >= 2 and parts[1].startswith('#'):
col_name = parts[0]
# Convert #1, #2, etc., to 0-based index
idx = int(parts[1].replace('#', '')) - 1
col_idx[col_name] = idx
Dynamically fetch column indices
idx_x = col_idx.get('_rlnCoordinateX')
idx_y = col_idx.get('_rlnCoordinateY')
idx_tube = col_idx.get('_rlnHelicalTubeID')
idx_image = col_idx.get('_rlnImageName')
idx_mic = col_idx.get('_rlnMicrographName')
=========================================
Process each line in the data
for line in data_r_star.split('
'):
if line.startswith("0"):
parts = line.split()
# Extract fields using automatically detected column indices
CoordinateX3 = float(parts[idx_x])
CoordinateY4 = float(parts[idx_y])
HelicalTubeID14 = parts[idx_tube]
ImageName1 = parts[idx_image]
MicrographName2 = parts[idx_mic]
# ====== Dynamic Micrograph Filename Extraction ======
# 1. Strip the folder path (e.g., 'J2/imported/')
base_name = os.path.basename(MicrographName2)
# 2. Strip leading numeric ID prefix (e.g., '000000741159697516169_')
name_parts = base_name.split('_', 1)
if len(name_parts) == 2 and name_parts[0].isdigit():
image_name = name_parts[1]
else:
image_name = base_name
# ====================================================
# Create star file in the output folder
star_file_path = os.path.join(output_folder, image_name_old.replace(".mrc", ".star"))
if HelicalTubeID14 == HelicalTubeID14_old and ck == 0:
cw = 1
ck = 1
l = 1
elif HelicalTubeID14 == HelicalTubeID14_old and ck == 1:
cw = 0
ck = 1
l = l + 1
elif HelicalTubeID14 != HelicalTubeID14_old and ck == 0:
cw = 0
ck = 0
elif HelicalTubeID14 != HelicalTubeID14_old and ck == 1:
cw = 1
ck = 0
l = 0
if cw == 1:
if os.path.exists(star_file_path):
# If it exists, append the coordinates
with open(star_file_path, 'a') as star_file:
star_file.write(f"{CoordinateX3_old} {4092-CoordinateY4_old} 2 -999.00000 -999.00000
")
else:
# If it doesn't exist, create the star file and write coordinates
with open(star_file_path, 'w') as star_file:
star_file.write("# version 30001
data_
loop_
_rlnCoordinateX #1
_rlnCoordinateY #2
_rlnParticleSelectionType #3
_rlnAnglePsi #4
_rlnAutopickFigureOfMerit #5
")
star_file.write(f"{CoordinateX3_old} {4092-CoordinateY4_old} 2 -999.00000 -999.00000
")
if l == 10:
if os.path.exists(star_file_path):
# If it exists, append the coordinates
with open(star_file_path, 'a') as star_file:
star_file.write(f"{CoordinateX3_old} {4092-CoordinateY4_old} 2 -999.00000 -999.00000
")
star_file.write(f"{CoordinateX3} {4092-CoordinateY4} 2 -999.00000 -999.00000
")
l = 0
print("Star files " + star_file_path + " created and updated successfully..")
image_name_old = image_name
CoordinateX3_old = CoordinateX3
CoordinateY4_old = CoordinateY4
HelicalTubeID14_old = HelicalTubeID14
